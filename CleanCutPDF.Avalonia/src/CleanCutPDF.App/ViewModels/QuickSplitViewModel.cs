using System.Collections.ObjectModel;
using CleanCutPDF.App.Services;
using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.Export;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Pdf;
using CleanCutPDF.Core.Services;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace CleanCutPDF.App.ViewModels;

public sealed partial class QuickSplitJobViewModel(string path) : ObservableObject
{
    public string FilePath { get; } = path;
    public string FileName { get; } = Path.GetFileName(path);

    [ObservableProperty]
    public partial string Status { get; set; } = "Waiting…";

    [ObservableProperty]
    public partial bool IsDone { get; set; }

    [ObservableProperty]
    public partial bool IsFailed { get; set; }

    public string? OutputFolder { get; set; }

    public override string ToString() => $"{FileName}, {Status}";
}

/// <summary>
/// Quick Split: for batches where each client has one document. Files are
/// split at SPLIT HERE pages and saved with generic names to
/// "Quick Split Files/YYYY-MM-DD" inside the export folder. Jobs run one after
/// another in the background.
/// </summary>
public sealed partial class QuickSplitViewModel : ObservableObject
{
    private readonly QuickSplitService _service;
    private readonly ISettingsService _settings;
    private readonly IDialogService _dialogs;
    private readonly IShellService _shell;
    private readonly ActivityService _activity;
    private readonly CrashLog _crashLog;
    private readonly ToolsService _tools;

    [RelayCommand]
    private Task SaveSplitHereSheetAsync() => _tools.SaveSplitHereTemplateAsync();
    private readonly SemaphoreSlim _queue = new(1, 1);
    private CancellationTokenSource _cts = new();
    private bool _syncing;

    public QuickSplitViewModel(QuickSplitService service, ISettingsService settings, IDialogService dialogs,
        IShellService shell, ActivityService activity, CrashLog crashLog, ToolsService tools)
    {
        _tools = tools;
        _service = service;
        _settings = settings;
        _dialogs = dialogs;
        _shell = shell;
        _activity = activity;
        _crashLog = crashLog;
        _settings.Changed += (_, current) =>
        {
            _syncing = true;
            FilenameOrder = current.QuickSplitFilenameOrder;
            _syncing = false;
        };
        FilenameOrder = settings.Current.QuickSplitFilenameOrder;
    }

    public ObservableCollection<QuickSplitJobViewModel> Jobs { get; } = [];

    public IReadOnlyList<string> FilenameOrders { get; } = QuickSplitOrders.All;

    public bool HasJobs => Jobs.Count > 0;

    [ObservableProperty]
    public partial string FilenameOrder { get; set; } = QuickSplitOrders.OriginalThenPart;

    [ObservableProperty]
    public partial string Example { get; private set; } = "";

    partial void OnFilenameOrderChanged(string value)
    {
        Example = $"Example: {QuickSplitService.FileName("Scan 2026-10-02", 1, value)}.pdf";
        if (!_syncing && QuickSplitOrders.All.Contains(value))
        {
            _settings.Update(s => s.QuickSplitFilenameOrder = value);
        }
    }

    [RelayCommand]
    private async Task OpenPdfsAsync()
    {
        var paths = await _dialogs.PickPdfFilesAsync("Quick Split PDFs");
        await SplitAsync(paths);
    }

    /// <summary>Also used when PDFs are dropped while this page is showing.</summary>
    public async Task SplitAsync(IReadOnlyList<string> paths)
    {
        var pdfs = paths.Where(DocumentStore.IsPdf).ToList();
        if (pdfs.Count == 0)
        {
            if (paths.Count > 0)
            {
                await _dialogs.ShowMessageAsync("Invalid Drop", "Only PDF files are supported.");
            }

            return;
        }

        var root = _settings.Current.ExportFolder;
        if (string.IsNullOrWhiteSpace(root) || !Directory.Exists(root))
        {
            // 1.x silently wrote next to the program when no export folder was set.
            root = await _dialogs.PickFolderAsync("Choose where to save Quick Split files");
            if (string.IsNullOrWhiteSpace(root))
            {
                return;
            }
        }

        var jobs = pdfs.Select(p => new QuickSplitJobViewModel(Path.GetFullPath(p))).ToList();
        foreach (var job in jobs)
        {
            Jobs.Insert(0, job);
        }

        OnPropertyChanged(nameof(HasJobs));
        foreach (var job in jobs)
        {
            await RunAsync(job, root);
        }
    }

    private async Task RunAsync(QuickSplitJobViewModel job, string root)
    {
        await _queue.WaitAsync();
        try
        {
            using var _ = _activity.Begin($"Quick splitting {job.FileName}");
            var progress = new Progress<string>(text => job.Status = text);
            var result = await _service.SplitAsync(job.FilePath, root, _settings.Current.QuickSplitFilenameOrder,
                _settings.Current.RemoveBlankPages, progress, _cts.Token);
            var skipped = result.Files.SelectMany(f => f.SkippedPages).ToList();
            job.OutputFolder = result.OutputFolder;
            job.Status = $"{result.Files.Count} file(s) saved to {result.OutputFolder}" +
                         (skipped.Count > 0 ? $" · blank pages removed: {string.Join(", ", skipped)}" : "") +
                         (result.NoMarkersFound ? " · no SPLIT HERE pages were found, so it was saved as one file" : "");
            job.IsDone = true;
        }
        catch (OperationCanceledException)
        {
            job.Status = "Cancelled; no files were kept.";
            job.IsFailed = true;
        }
        catch (Exception error)
        {
            _crashLog.Write($"Quick Split of {job.FileName} failed", error);
            job.Status = error is PdfOpenException ? error.Message : $"Failed: {error.Message}";
            job.IsFailed = true;
        }
        finally
        {
            _queue.Release();
        }
    }

    [RelayCommand]
    private void CancelAll()
    {
        _cts.Cancel();
        _cts = new CancellationTokenSource();
    }

    [RelayCommand]
    private async Task OpenFolderAsync(QuickSplitJobViewModel? job)
    {
        var folder = job?.OutputFolder;
        if (folder is not null && _shell.OpenFolder(folder, "Quick Split folder") is { } error)
        {
            await _dialogs.ShowMessageAsync("Open Folder", error);
        }
    }

    [RelayCommand]
    private void ClearFinished()
    {
        foreach (var job in Jobs.Where(j => j.IsDone || j.IsFailed).ToList())
        {
            Jobs.Remove(job);
        }

        OnPropertyChanged(nameof(HasJobs));
    }
}
