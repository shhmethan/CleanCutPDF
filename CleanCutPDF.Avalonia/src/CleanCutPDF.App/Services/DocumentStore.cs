using System.Collections.ObjectModel;
using Avalonia.Threading;
using CleanCutPDF.App.ViewModels;
using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Models;
using CleanCutPDF.Core.Pdf;
using CleanCutPDF.Core.Services;
using CleanCutPDF.Core.Sessions;
using CommunityToolkit.Mvvm.ComponentModel;

namespace CleanCutPDF.App.Services;

public sealed record ImportResult(int Added, IReadOnlyList<string> Duplicates, IReadOnlyList<string> Skipped);

public sealed partial class FolderViewModel(string id, string name) : ObservableObject
{
    public string Id { get; } = id;

    [ObservableProperty]
    public partial string Name { get; set; } = name;

    public bool IsInbox => Id == SessionFolder.InboxId;
}

/// <summary>
/// The open PDFs shared by the Inbox and the editor. Imports add rows at once
/// and fill in page counts in the background; SPLIT HERE detection then runs
/// one document at a time at low priority (the document being edited jumps
/// the queue). Everything is saved to sessions.json shortly after it changes.
/// All public members must be used on the UI thread.
/// </summary>
public sealed partial class DocumentStore : ObservableObject
{
    private const int MaxConcurrentFileReads = 4;

    private readonly IPdfEngine _engine;
    private readonly PagePreviewService _previews;
    private readonly ISettingsService _settings;
    private readonly ActivityService _activity;
    private readonly CrashLog _crashLog;
    private readonly AppLog _log;
    private readonly SessionStore _sessions;
    private readonly SplitDetector _detector;
    private readonly SemaphoreSlim _backgroundDetection = new(1, 1);
    private CancellationTokenSource? _pendingSave;
    private bool _restoring;

    public DocumentStore(IPdfEngine engine, PagePreviewService previews, ISettingsService settings,
        ActivityService activity, CrashLog crashLog, AppLog log, SessionStore sessions)
    {
        _engine = engine;
        _previews = previews;
        _settings = settings;
        _activity = activity;
        _crashLog = crashLog;
        _log = log;
        _sessions = sessions;
        _detector = new SplitDetector(engine, log);
        Folders.Add(new FolderViewModel(SessionFolder.InboxId, "Inbox"));
    }

    public ObservableCollection<DocumentItemViewModel> Documents { get; } = [];

    public ObservableCollection<FolderViewModel> Folders { get; } = [];

    /// <summary>The document shown in the Split &amp; Rename editor.</summary>
    [ObservableProperty]
    public partial DocumentItemViewModel? ActiveDocument { get; set; }

    /// <summary>Files written by the most recent export (for Undo Last Export, Phase 4).</summary>
    public IReadOnlyList<string> LastExportedFiles { get; set; } = [];

    /// <summary>Raised before saving so the open editor can copy its field values into the document.</summary>
    public event EventHandler? CapturingSession;

    /// <summary>Asks the open editor to copy its values into its document now.</summary>
    public void CaptureEditor() => CapturingSession?.Invoke(this, EventArgs.Empty);

    /// <summary>Raised when a document finishes split detection.</summary>
    public event EventHandler<DocumentItemViewModel>? DetectionCompleted;

    partial void OnActiveDocumentChanged(DocumentItemViewModel? value)
    {
        if (value is { IsReady: true, Detection: DetectionState.NotStarted })
        {
            _ = DetectAsync(value, jumpQueue: true);
        }
        else
        {
            // Waiting behind other documents: start it now.
            value?.DetectionPromotion?.TrySetResult();
        }
    }

    // ───── Import ─────

    public async Task<ImportResult> ImportAsync(IEnumerable<string> paths, string workspace, string folderId,
        CancellationToken cancellationToken)
    {
        var duplicates = new List<string>();
        var skipped = new List<string>();
        var added = new List<DocumentItemViewModel>();

        foreach (var raw in paths)
        {
            string fullPath;
            try
            {
                fullPath = Path.GetFullPath(raw);
            }
            catch (Exception)
            {
                skipped.Add(raw);
                continue;
            }

            if (!IsPdf(fullPath))
            {
                skipped.Add(Path.GetFileName(fullPath));
                continue;
            }

            if (Find(fullPath) is not null || added.Any(d => SamePath(d.FilePath, fullPath)))
            {
                duplicates.Add(Path.GetFileName(fullPath));
                continue;
            }

            var item = new DocumentItemViewModel(fullPath, workspace) { FolderId = folderId };
            Documents.Add(item);
            added.Add(item);
        }

        _log.Info("Import", $"Requested {added.Count + duplicates.Count + skipped.Count} file(s): " +
                            $"{added.Count} new, {duplicates.Count} already open, {skipped.Count} skipped; workspace {workspace}");
        if (added.Count == 0)
        {
            return new ImportResult(0, duplicates, skipped);
        }

        using (_activity.Begin(added.Count == 1 ? $"Opening {added[0].FileName}" : $"Opening {added.Count} PDFs"))
        {
            using var throttle = new SemaphoreSlim(MaxConcurrentFileReads);
            await Task.WhenAll(added.Select(item => LoadOneAsync(item, throttle, cancellationToken)));
        }

        RequestSave();
        foreach (var item in added.Where(i => i.IsReady))
        {
            _ = DetectAsync(item, jumpQueue: false);
        }

        return new ImportResult(added.Count, duplicates, skipped);
    }

    public static bool IsPdf(string path) =>
        string.Equals(Path.GetExtension(path), ".pdf", StringComparison.OrdinalIgnoreCase);

    private async Task LoadOneAsync(DocumentItemViewModel item, SemaphoreSlim throttle, CancellationToken cancellationToken)
    {
        try
        {
            await throttle.WaitAsync(cancellationToken);
            try
            {
                var started = System.Diagnostics.Stopwatch.GetTimestamp();
                var info = await _engine.OpenAsync(item.FilePath, cancellationToken);
                item.PageCount = info.PageCount;
                item.Signature = info.Signature;
                item.State = DocumentLoadState.Ready;
                _log.Info("Import", $"Opened {item.FileName}: {info.PageCount} page(s) in " +
                                    $"{System.Diagnostics.Stopwatch.GetElapsedTime(started).TotalMilliseconds:N0} ms");
            }
            finally
            {
                throttle.Release();
            }
        }
        catch (OperationCanceledException)
        {
            Documents.Remove(item);
            _log.Info("Import", $"Cancelled {item.FileName}");
        }
        catch (PdfOpenException error)
        {
            _log.Warning("Import", $"Could not open {item.FileName}: {error.Message}");
            item.ErrorMessage = error.Message;
            item.State = DocumentLoadState.Failed;
        }
        catch (Exception error)
        {
            _crashLog.Write($"Opening {item.FileName} failed", error);
            item.ErrorMessage = "Unexpected error while opening this PDF. Details were saved to the log.";
            item.State = DocumentLoadState.Failed;
        }
    }

    // ───── Split detection ─────

    private async Task DetectAsync(DocumentItemViewModel item, bool jumpQueue)
    {
        if (item.Detection is DetectionState.Running or DetectionState.Done || !item.IsReady)
        {
            return;
        }

        var cts = new CancellationTokenSource();
        item.DetectionCts = cts;
        item.Detection = DetectionState.Running;
        item.PagesScanned = 0;
        var waited = false;
        try
        {
            if (!jumpQueue)
            {
                var promotion = item.DetectionPromotion = new TaskCompletionSource();
                var slot = _backgroundDetection.WaitAsync(cts.Token);
                if (await Task.WhenAny(slot, promotion.Task) == slot)
                {
                    await slot;
                    waited = true;
                }
                else
                {
                    // Promoted because the user opened it; hand back the slot whenever it arrives.
                    _ = slot.ContinueWith(t =>
                    {
                        if (t.Status == TaskStatus.RanToCompletion)
                        {
                            _backgroundDetection.Release();
                        }
                    }, TaskScheduler.Default);
                }

                item.DetectionPromotion = null;
            }

            using var busy = _activity.Begin($"Finding SPLIT HERE pages in {item.FileName}");
            var progress = new Progress<DetectionProgress>(p => item.PagesScanned = p.PagesDone);
            var result = await _detector.DetectAsync(item.FilePath, progress, cts.Token);
            ApplyRanges(item, result.Ranges, result.MarkerPages);
            item.PageCount = result.PageCount;
            item.Detection = DetectionState.Done;
            RequestSave();
        }
        catch (OperationCanceledException)
        {
            item.Detection = DetectionState.NotStarted;
        }
        catch (Exception error)
        {
            _crashLog.Write($"Split detection failed for {item.FileName}", error);
            ApplyRanges(item, [new PageRange(0, Math.Max(0, item.PageCount - 1))], []);
            item.Detection = DetectionState.Failed;
        }
        finally
        {
            if (waited)
            {
                _backgroundDetection.Release();
            }

            if (ReferenceEquals(item.DetectionCts, cts))
            {
                item.DetectionCts = null;
            }

            cts.Dispose();
        }

        if (item.Detection is DetectionState.Done or DetectionState.Failed)
        {
            DetectionCompleted?.Invoke(this, item);
        }
    }

    private static void ApplyRanges(DocumentItemViewModel item, IReadOnlyList<PageRange> ranges, IReadOnlyList<int> markers)
    {
        item.MarkerPages = markers;
        item.WorkspaceData = SessionStore.Reconcile(item.WorkspaceData, ranges.Count);
        item.Ranges = ranges;
    }

    // ───── Organizing ─────

    public DocumentItemViewModel? Find(string path) => Documents.FirstOrDefault(d => SamePath(d.FilePath, path));

    /// <summary>Closes documents. The original files on disk are never touched.</summary>
    public void Close(IEnumerable<DocumentItemViewModel> items)
    {
        foreach (var item in items.ToList())
        {
            _log.Info("Documents", $"Closed {item.FileName}");
            item.DetectionCts?.Cancel();
            Documents.Remove(item);
            if (ReferenceEquals(ActiveDocument, item))
            {
                // Clearing the active document clears the preview immediately,
                // so a closed PDF can never remain visible.
                ActiveDocument = null;
            }

            _ = ForgetAsync(item.FilePath);
        }

        RequestSave();
    }

    public FolderViewModel CreateFolder(string name)
    {
        var folder = new FolderViewModel($"folder-{Guid.NewGuid():N}"[..19], name.Trim());
        Folders.Add(folder);
        _log.Info("Folders", $"Created folder {folder.Id}");
        RequestSave();
        return folder;
    }

    public bool FolderNameExists(string name, string? exceptId = null) =>
        Folders.Any(f => f.Id != exceptId && string.Equals(f.Name, name.Trim(), StringComparison.OrdinalIgnoreCase));

    public void RenameFolder(FolderViewModel folder, string name)
    {
        if (folder.IsInbox)
        {
            return;
        }

        folder.Name = name.Trim();
        RequestSave();
    }

    /// <summary>Deletes a folder; its PDFs move to Inbox (the files themselves are not touched).</summary>
    public void DeleteFolder(FolderViewModel folder)
    {
        if (folder.IsInbox)
        {
            return;
        }

        foreach (var document in Documents.Where(d => d.FolderId == folder.Id))
        {
            document.FolderId = SessionFolder.InboxId;
        }

        Folders.Remove(folder);
        _log.Info("Folders", $"Deleted folder {folder.Id}; documents moved to Inbox");
        RequestSave();
    }

    /// <summary>Moves a folder up or down; Inbox always stays first.</summary>
    public void MoveFolder(FolderViewModel folder, int direction)
    {
        var index = Folders.IndexOf(folder);
        var target = index + direction;
        if (folder.IsInbox || index < 0 || target < 1 || target >= Folders.Count)
        {
            return;
        }

        Folders.Move(index, target);
        RequestSave();
    }

    public void MoveToFolder(IEnumerable<DocumentItemViewModel> items, string folderId)
    {
        foreach (var item in items)
        {
            item.FolderId = folderId;
        }

        RequestSave();
    }

    // ───── Session persistence ─────

    /// <summary>Saves shortly after the last change, so typing never waits on the disk.</summary>
    public void RequestSave()
    {
        if (_restoring)
        {
            return;
        }

        _pendingSave?.Cancel();
        var cts = _pendingSave = new CancellationTokenSource();
        _ = SaveSoonAsync(cts.Token);
    }

    private async Task SaveSoonAsync(CancellationToken token)
    {
        try
        {
            await Task.Delay(TimeSpan.FromSeconds(1.5), token);
            await SaveNowAsync();
        }
        catch (OperationCanceledException)
        {
        }
    }

    public async Task SaveNowAsync()
    {
        if (!Dispatcher.UIThread.CheckAccess())
        {
            await Dispatcher.UIThread.InvokeAsync(SaveNowAsync);
            return;
        }

        try
        {
            CapturingSession?.Invoke(this, EventArgs.Empty);
            var state = new SessionState
            {
                Folders = Folders.Select(f => new SessionFolder { Id = f.Id, Name = f.Name }).ToList(),
                Documents = Documents.Where(d => !d.IsFailed).Select(d => new SessionDocument
                {
                    FilePath = d.FilePath,
                    ClientName = d.ClientName,
                    Workspace = d.Workspace,
                    FolderId = d.FolderId,
                    PageCount = d.PageCount,
                    FileSignature = d.Signature,
                    DetectedRanges = d.IsDetected ? d.Ranges.ToList() : null,
                    MarkerPages = d.MarkerPages.ToList(),
                    WorkspaceData = d.WorkspaceData.ToDictionary(p => p.Key, p => p.Value.Select(r => new Dictionary<string, string>(r)).ToList())
                }).ToList()
            };
            await _sessions.SaveAsync(state);
            _log.Debug("Session", $"Saved {state.Documents.Count} document(s)");
        }
        catch (Exception error)
        {
            _crashLog.Write("Saving the session failed", error);
        }
    }

    /// <summary>
    /// Restores the previous session without opening any editor. Documents whose
    /// file is unchanged reuse their cached page count and SPLIT HERE ranges, so
    /// startup does not re-scan every PDF.
    /// </summary>
    public async Task RestoreAsync(IReadOnlyCollection<string> knownWorkspaces) =>
        await AddSessionAsync(await _sessions.LoadAsync(), knownWorkspaces, replaceFolders: true);

    /// <summary>
    /// Adds documents and folders from a saved session (restore) or from the
    /// 1.x import (merge). Documents whose file is unchanged reuse their cached
    /// SPLIT HERE ranges, so they are not scanned again.
    /// </summary>
    public async Task<int> AddSessionAsync(SessionState state, IReadOnlyCollection<string> knownWorkspaces, bool replaceFolders)
    {
        var added = 0;
        _restoring = true;
        try
        {
            if (replaceFolders)
            {
                Folders.Clear();
            }

            foreach (var folder in state.Folders.Where(f => Folders.All(existing => existing.Id != f.Id)))
            {
                Folders.Add(new FolderViewModel(folder.Id, folder.Name));
            }

            var reopen = new List<(DocumentItemViewModel Item, SessionDocument Saved)>();
            var missing = 0;
            foreach (var saved in state.Documents)
            {
                if (!File.Exists(saved.FilePath) || Find(saved.FilePath) is not null)
                {
                    missing += File.Exists(saved.FilePath) ? 0 : 1;
                    continue;
                }

                var workspace = knownWorkspaces.Contains(saved.Workspace) ? saved.Workspace : _settings.Current.DefaultWorkspace;
                var item = new DocumentItemViewModel(saved.FilePath, workspace)
                {
                    FolderId = Folders.Any(f => f.Id == saved.FolderId) ? saved.FolderId : SessionFolder.InboxId,
                    ClientName = saved.ClientName,
                    WorkspaceData = saved.WorkspaceData
                };

                var signature = FileSignature.TryRead(saved.FilePath);
                var unchanged = signature is not null && signature == saved.FileSignature;
                if (unchanged && saved.PageCount > 0)
                {
                    item.PageCount = saved.PageCount;
                    item.Signature = signature;
                    item.State = DocumentLoadState.Ready;
                    UseCachedRanges(item, saved);
                }
                else
                {
                    reopen.Add((item, saved)); // Needs reading (changed on disk, or page count unknown).
                }

                Documents.Add(item);
                added++;
            }

            _log.Info("Session", $"Added {added} document(s) from saved session; {Folders.Count - 1} folder(s); " +
                                 $"{reopen.Count} to re-read, {missing} no longer exist");

            using var throttle = new SemaphoreSlim(MaxConcurrentFileReads);
            await Task.WhenAll(reopen.Select(entry => LoadOneAsync(entry.Item, throttle, CancellationToken.None)));
            foreach (var (item, saved) in reopen.Where(r => r.Item.IsReady && r.Item.Signature == r.Saved.FileSignature))
            {
                UseCachedRanges(item, saved);
            }
        }
        finally
        {
            _restoring = false;
        }

        foreach (var item in Documents.Where(d => d is { IsReady: true, Detection: DetectionState.NotStarted }).ToList())
        {
            _ = DetectAsync(item, jumpQueue: false);
        }

        RequestSave();
        return added;
    }

    private static void UseCachedRanges(DocumentItemViewModel item, SessionDocument saved)
    {
        if (saved.DetectedRanges is { Count: > 0 } ranges && ranges.All(r => r.End < Math.Max(1, item.PageCount)))
        {
            ApplyRanges(item, ranges, saved.MarkerPages);
            item.Detection = DetectionState.Done;
        }
    }

    private async Task ForgetAsync(string path)
    {
        try
        {
            await _previews.ForgetDocumentAsync(path);
        }
        catch (Exception error)
        {
            _crashLog.Write($"Releasing {Path.GetFileName(path)} failed", error);
        }
    }

    private static bool SamePath(string a, string b) =>
        string.Equals(a, b, OperatingSystem.IsWindows() || OperatingSystem.IsMacOS()
            ? StringComparison.OrdinalIgnoreCase
            : StringComparison.Ordinal);
}
