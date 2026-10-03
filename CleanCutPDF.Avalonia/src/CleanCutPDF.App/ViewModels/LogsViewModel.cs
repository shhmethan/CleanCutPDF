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
public sealed record HistoryGroupRow(HistoryGroup Group, string? DateHeading)
{
    public bool ShowDateHeading => DateHeading is not null;
    public string Heading => Group.Heading;
    public IReadOnlyList<HistoryEntry> Entries => Group.Entries;
    public override string ToString() => $"{Group.Heading}, {Group.Entries.Count} file(s)";
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
    private IReadOnlyList<HistoryEntry> _all = [];
    private IReadOnlyList<HistoryEntry> _visible = [];
    private CancellationTokenSource? _filterCts;
    private bool _loaded;
    private int _generation;

    public LogsViewModel(ExportHistory history, IPdfEngine engine, IDialogService dialogs, IShellService shell,
        ToolsService tools, DocumentStore documents, ActivityService activity, CrashLog crashLog, AppLog log)
    {
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
                Groups.Add(new HistoryGroupRow(group, heading));
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
        if (_visible.Count == 0)
        {
            await _dialogs.ShowMessageAsync("Export History", "No entries match the current search and filters.");
            return;
        }

        var choice = await _dialogs.ChooseAsync("Export History",
            $"Export the {_visible.Count} entr{(_visible.Count == 1 ? "y" : "ies")} currently shown as:",
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
            var bytes = await HistoryLog.ExportAsync(_visible, format, _engine);
            await File.WriteAllBytesAsync(path, bytes);
            _log.Info("Logs", $"Exported {_visible.Count} history entr(ies) as {format}");
            if (await _dialogs.ConfirmAsync("Export History", $"Saved {_visible.Count} entr(ies) to:\n{path}", "Open It", "Close")
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
        if (_visible.Count == 0)
        {
            await _dialogs.ShowMessageAsync("Print History", "No entries match the current search and filters.");
            return;
        }

        try
        {
            var path = Path.Combine(Path.GetTempPath(), $"CleanCutPDF history {DateTime.Now:yyyyMMdd-HHmmss}.html");
            await File.WriteAllBytesAsync(path, await HistoryLog.ExportAsync(_visible, HistoryExportFormat.Html, _engine));
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
