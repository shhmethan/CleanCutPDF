using System.Collections.ObjectModel;
using System.ComponentModel;
using CleanCutPDF.App.Services;
using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.Export;
using CleanCutPDF.Core.History;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Pdf;
using CleanCutPDF.Core.Services;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace CleanCutPDF.App.ViewModels;

/// <summary>One client's files on one day, with a date heading when the day changes.</summary>
public sealed record HistoryGroupRow(HistoryGroup Group, string? DateHeading, IReadOnlyList<HistoryEntryRow> Entries)
{
    public bool ShowDateHeading => DateHeading is not null;
    public string Heading => Group.Heading;
    public override string ToString() => $"{Group.Heading}, {Group.Entries.Count} file(s)";
}

/// <summary>One file on the Logs page; ticked rows are what Export and Print use.</summary>
public sealed partial class HistoryEntryRow(HistoryEntry entry, bool isChecked, LogsViewModel owner)
    : ObservableObject
{
    public HistoryEntry Entry { get; } = entry;

    /// <summary>The page, for the right-click menu (a ContextMenu is outside the page's visual tree).</summary>
    public LogsViewModel Owner { get; } = owner;

    public string Time => Entry.Time;
    public string File => Entry.File;
    public string Details => Entry.Details;
    public string Raw => Entry.Raw;
    public bool HasClient => Entry.Client.Length > 0;
    public string HideClientText => $"Stop Suggesting “{Entry.Client}”";

    [ObservableProperty]
    public partial bool IsChecked { get; set; } = isChecked;

    partial void OnIsCheckedChanged(bool value) => Owner.OnRowChecked(this);

    public override string ToString() => Entry.File;
}

public sealed record SortOption(HistorySort Sort, string Label)
{
    public override string ToString() => Label;
}

/// <summary>
/// Logs page: the export history grouped by day and client, with search,
/// filters, export, Clear Log, and Undo Last Export. Reading and filtering run
/// in the background and searching waits for a pause in typing, so a long
/// history never slows the window (1.x rebuilt every row on each keystroke).
/// </summary>
public sealed partial class LogsViewModel : ObservableObject
{
    private static readonly IReadOnlyDictionary<string, (HistoryExportFormat Format, string Extension, string Type)> Formats =
        new Dictionary<string, (HistoryExportFormat, string, string)>
        {
            ["CSV (Excel)"] = (HistoryExportFormat.Csv, "csv", "CSV files"),
            ["TSV (tab-separated)"] = (HistoryExportFormat.Tsv, "tsv", "TSV files"),
            ["Text"] = (HistoryExportFormat.Txt, "txt", "Text files"),
            ["PDF"] = (HistoryExportFormat.Pdf, "pdf", "PDF files")
        };

    private readonly ExportHistory _history;
    private readonly IPdfEngine _engine;
    private readonly IDialogService _dialogs;
    private readonly IShellService _shell;
    private readonly ToolsService _tools;
    private readonly DocumentStore _documents;
    private readonly ActivityService _activity;
    private readonly CrashLog _crashLog;
    private readonly AppLog _log;
    private readonly ClientSuggestions _clients;
    private readonly HashSet<HistoryEntry> _checked = [];
    private IReadOnlyList<HistoryEntry> _all = [];
    private IReadOnlyList<HistoryEntry> _visible = [];
    private CancellationTokenSource? _filterCts;
    private bool _loaded;
    private int _generation;

    public LogsViewModel(ExportHistory history, IPdfEngine engine, IDialogService dialogs, IShellService shell,
        ToolsService tools, DocumentStore documents, ActivityService activity, CrashLog crashLog, AppLog log,
        ClientSuggestions clients)
    {
        _clients = clients;
        _history = history;
        _engine = engine;
        _dialogs = dialogs;
        _shell = shell;
        _tools = tools;
        _documents = documents;
        _activity = activity;
        _crashLog = crashLog;
        _log = log;
        SelectedSort = SortOptions[0];
        _history.Changed += (_, _) => Avalonia.Threading.Dispatcher.UIThread.Post(() =>
        {
            if (_loaded)
            {
                _ = ReloadAsync();
            }
        });
        _documents.PropertyChanged += (_, e) =>
        {
            if (e.PropertyName == nameof(DocumentStore.LastExportedFiles))
            {
                UndoLastExportCommand.NotifyCanExecuteChanged();
            }
        };
    }

    public ObservableCollection<HistoryGroupRow> Groups { get; } = [];

    public IReadOnlyList<SortOption> SortOptions { get; } =
    [
        new(HistorySort.NewestFirst, "Date (newest first)"),
        new(HistorySort.OldestFirst, "Date (oldest first)"),
        new(HistorySort.ClientAToZ, "Client A → Z"),
        new(HistorySort.ClientZToA, "Client Z → A")
    ];

    [ObservableProperty]
    public partial string Search { get; set; } = "";

    [ObservableProperty]
    public partial string WorkspaceFilter { get; set; } = "";

    [ObservableProperty]
    public partial DateTime? FromDate { get; set; }

    [ObservableProperty]
    public partial DateTime? ToDate { get; set; }

    [ObservableProperty]
    public partial SortOption SelectedSort { get; set; }

    [ObservableProperty]
    public partial string Summary { get; private set; } = "Loading…";

    [ObservableProperty]
    public partial bool IsEmpty { get; private set; }

    [ObservableProperty]
    public partial bool IsBusy { get; private set; }

    public bool HasChecked => _checked.Count > 0;
    public string CheckedText => $"{_checked.Count} selected; Export and Print use only these";

    /// <summary>Called when the page is first shown.</summary>
    public async Task EnsureLoadedAsync()
    {
        if (!_loaded)
        {
            _loaded = true;
            await ReloadAsync();
        }
    }

    private async Task ReloadAsync()
    {
        try
        {
            var lines = await _history.ReadLinesAsync();
            _all = await Task.Run(() => HistoryLog.Parse(lines));
            _checked.IntersectWith(_all);
            NotifyChecked();
            await ApplyFilterAsync(debounce: false);
        }
        catch (Exception error)
        {
            _crashLog.Write("Reading the export history failed", error);
            Summary = "The export history could not be read. Details were saved to the diagnostic log.";
        }
    }

    protected override void OnPropertyChanged(PropertyChangedEventArgs e)
    {
        base.OnPropertyChanged(e);
        if (_loaded && e.PropertyName is nameof(Search) or nameof(WorkspaceFilter) or nameof(FromDate) or nameof(ToDate)
                or nameof(SelectedSort))
        {
            _ = ApplyFilterAsync(debounce: e.PropertyName is nameof(Search) or nameof(WorkspaceFilter));
        }
    }

    private async Task ApplyFilterAsync(bool debounce)
    {
        _filterCts?.Cancel();
        var cts = _filterCts = new CancellationTokenSource();
        var generation = ++_generation;
        try
        {
            if (debounce)
            {
                await Task.Delay(250, cts.Token);
            }

            var filter = new HistoryFilter(Search, WorkspaceFilter,
                FromDate is { } from ? DateOnly.FromDateTime(from) : null,
                ToDate is { } to ? DateOnly.FromDateTime(to) : null,
                SelectedSort.Sort);
            var all = _all;
            var (visible, groups) = await Task.Run(() =>
            {
                var filtered = HistoryLog.Filter(all, filter);
                return (filtered, HistoryLog.Group(filtered));
            }, cts.Token);
            if (generation != _generation)
            {
                return;
            }

            _visible = visible;
            Groups.Clear();
            string? lastDate = null;
            foreach (var group in groups)
            {
                var heading = group.Date != lastDate ? FormatDate(group.Date) : null;
                lastDate = group.Date;
                var rows = group.Entries.Select(e => new HistoryEntryRow(e, _checked.Contains(e), this)).ToList();
                Groups.Add(new HistoryGroupRow(group, heading, rows));
            }

            IsEmpty = visible.Count == 0;
            Summary = _all.Count == 0
                ? "No exports yet. Files you export or rename appear here."
                : visible.Count == _all.Count
                    ? $"{_all.Count} file(s)"
                    : $"Showing {visible.Count} of {_all.Count} file(s)";
        }
        catch (OperationCanceledException)
        {
        }
    }

    internal void OnRowChecked(HistoryEntryRow row)
    {
        if (row.IsChecked)
        {
            _checked.Add(row.Entry);
        }
        else
        {
            _checked.Remove(row.Entry);
        }

        NotifyChecked();
    }

    private void NotifyChecked()
    {
        OnPropertyChanged(nameof(HasChecked));
        OnPropertyChanged(nameof(CheckedText));
    }

    /// <summary>The ticked entries (in the current sort), or everything shown when nothing is ticked.</summary>
    private IReadOnlyList<HistoryEntry> Chosen() =>
        _checked.Count == 0
            ? _visible
            : HistoryLog.Filter(_all.Where(_checked.Contains).ToList(), new HistoryFilter(Sort: SelectedSort.Sort));

    [RelayCommand]
    private void ClearSelection()
    {
        foreach (var row in Groups.SelectMany(g => g.Entries))
        {
            row.IsChecked = false;
        }

        _checked.Clear(); // Also ticked entries hidden by the current filters.
        NotifyChecked();
    }

    [RelayCommand]
    private void SelectShown()
    {
        foreach (var row in Groups.SelectMany(g => g.Entries))
        {
            row.IsChecked = true;
        }
    }

    // ───── Right-click menu ─────

    [RelayCommand]
    private Task CopyFileName(HistoryEntryRow? row) => row is null ? Task.CompletedTask : CopyAsync(row.Entry.File);

    [RelayCommand]
    private Task CopyDetails(HistoryEntryRow? row) =>
        row is null ? Task.CompletedTask : CopyAsync($"{row.Entry.File}{Environment.NewLine}{row.Entry.Details}");

    [RelayCommand]
    private Task CopyClient(HistoryEntryRow? row) => row is null ? Task.CompletedTask : CopyAsync(row.Entry.Client);

    [RelayCommand]
    private Task CopyLogLine(HistoryEntryRow? row) => row is null ? Task.CompletedTask : CopyAsync(row.Entry.Raw);

    private async Task CopyAsync(string text)
    {
        try
        {
            await _dialogs.CopyTextAsync(text);
            _activity.Report("Copied to the clipboard");
        }
        catch (Exception error)
        {
            _log.Warning("Logs", "Copy to the clipboard failed", error);
        }
    }

    [RelayCommand]
    private void HideClient(HistoryEntryRow? row)
    {
        if (row is { HasClient: true })
        {
            _clients.Hide(row.Entry.Client);
            _activity.Report($"“{row.Entry.Client}” will no longer be suggested (undo in Settings › Client name suggestions)");
        }
    }

    private static string FormatDate(string isoDate) =>
        DateOnly.TryParseExact(isoDate, "yyyy-MM-dd", out var date) ? date.ToString("dddd, MMMM d, yyyy") : isoDate;

    [RelayCommand]
    private void ClearFilters()
    {
        Search = "";
        WorkspaceFilter = "";
        FromDate = null;
        ToDate = null;
    }

    [RelayCommand]
    private async Task ExportAsync()
    {
        var chosen = Chosen();
        if (chosen.Count == 0)
        {
            await _dialogs.ShowMessageAsync("Export History", "No entries match the current search and filters.");
            return;
        }

        var choice = await _dialogs.ChooseAsync("Export History",
            $"Export the {chosen.Count} {(_checked.Count > 0 ? "selected" : "currently shown")} entr{(chosen.Count == 1 ? "y" : "ies")} as:",
            Formats.Keys.ToList(), "CSV (Excel)", "Next");
        if (choice is null)
        {
            return;
        }

        var (format, extension, type) = Formats[choice];
        var path = await _dialogs.SaveFileAsync("Export History", $"CleanCutPDF history {DateTime.Now:yyyy-MM-dd}.{extension}",
            extension, type);
        if (path is null)
        {
            return;
        }

        IsBusy = true;
        try
        {
            using var busy = _activity.Begin("Exporting history");
            var bytes = await HistoryLog.ExportAsync(chosen, format, _engine);
            await File.WriteAllBytesAsync(path, bytes);
            _log.Info("Logs", $"Exported {chosen.Count} history entr(ies) as {format}");
            if (await _dialogs.ConfirmAsync("Export History", $"Saved {chosen.Count} entr(ies) to:\n{path}", "Open It", "Close")
                && _shell.OpenFile(path) is { } error)
            {
                await _dialogs.ShowMessageAsync("Open File", error);
            }
        }
        catch (Exception error)
        {
            _crashLog.Write("Exporting the history failed", error);
            await _dialogs.ShowMessageAsync("Export History", $"The history could not be exported.\n\n{error.Message}");
        }
        finally
        {
            IsBusy = false;
        }
    }

    /// <summary>Opens a printable page in the browser (1.x Print option).</summary>
    [RelayCommand]
    private async Task PrintAsync()
    {
        var chosen = Chosen();
        if (chosen.Count == 0)
        {
            await _dialogs.ShowMessageAsync("Print History", "No entries match the current search and filters.");
            return;
        }

        try
        {
            var path = Path.Combine(Path.GetTempPath(), $"CleanCutPDF history {DateTime.Now:yyyyMMdd-HHmmss}.html");
            await File.WriteAllBytesAsync(path, await HistoryLog.ExportAsync(chosen, HistoryExportFormat.Html, _engine));
            if (_shell.OpenFile(path) is { } error)
            {
                await _dialogs.ShowMessageAsync("Print History", error);
            }
        }
        catch (Exception error)
        {
            _crashLog.Write("Printing the history failed", error);
            await _dialogs.ShowMessageAsync("Print History", $"The print page could not be created.\n\n{error.Message}");
        }
    }

    [RelayCommand]
    private async Task ClearLogAsync()
    {
        if (_all.Count == 0 ||
            !await _dialogs.ConfirmAsync("Clear Log",
                $"Clear the export history ({_all.Count} file(s))?\n\nThe current history file goes to the Recycle Bin, so it can be restored. " +
                "Your exported PDFs are not affected.", "Clear Log"))
        {
            return;
        }

        var problem = await _history.ClearAsync();
        _log.Info("Logs", "Export history cleared");
        if (problem is not null)
        {
            await _dialogs.ShowMessageAsync("Clear Log",
                $"The history was cleared, but the old file could not be moved to the Recycle Bin ({problem}). " +
                "It was kept in the CleanCutPDF data folder.");
        }
    }

    [RelayCommand(CanExecute = nameof(CanUndo))]
    private Task UndoLastExportAsync() => _tools.UndoLastExportAsync();

    private bool CanUndo() => _tools.CanUndo;
}
