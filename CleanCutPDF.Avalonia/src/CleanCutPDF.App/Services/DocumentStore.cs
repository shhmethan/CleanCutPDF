using System.Collections.ObjectModel;
using CleanCutPDF.App.ViewModels;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Pdf;
using CleanCutPDF.Core.Services;
using CommunityToolkit.Mvvm.ComponentModel;

namespace CleanCutPDF.App.Services;

public sealed record ImportResult(int Added, IReadOnlyList<string> Duplicates, IReadOnlyList<string> Skipped);

/// <summary>
/// The set of open PDFs shared by the Inbox and the editors. Imports add rows
/// immediately and fill in page counts in the background, so a large batch
/// never freezes the window.
/// </summary>
public sealed partial class DocumentStore(
    IPdfEngine engine,
    PagePreviewService previews,
    ISettingsService settings,
    ActivityService activity,
    CrashLog crashLog) : ObservableObject
{
    private const int MaxConcurrentFileReads = 4;

    public ObservableCollection<DocumentItemViewModel> Documents { get; } = [];

    /// <summary>The document shown in the Split &amp; Rename editor.</summary>
    [ObservableProperty]
    public partial DocumentItemViewModel? ActiveDocument { get; set; }

    /// <summary>Must be called on the UI thread.</summary>
    public async Task<ImportResult> ImportAsync(IEnumerable<string> paths, CancellationToken cancellationToken)
    {
        var duplicates = new List<string>();
        var skipped = new List<string>();
        var added = new List<DocumentItemViewModel>();
        var workspace = settings.Current.DefaultWorkspace;

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

            if (!string.Equals(Path.GetExtension(fullPath), ".pdf", StringComparison.OrdinalIgnoreCase))
            {
                skipped.Add(Path.GetFileName(fullPath));
                continue;
            }

            if (Documents.Any(d => SamePath(d.FilePath, fullPath)) || added.Any(d => SamePath(d.FilePath, fullPath)))
            {
                duplicates.Add(Path.GetFileName(fullPath));
                continue;
            }

            var item = new DocumentItemViewModel(fullPath, workspace);
            Documents.Add(item);
            added.Add(item);
        }

        if (added.Count == 0)
        {
            return new ImportResult(0, duplicates, skipped);
        }

        using var _ = activity.Begin(added.Count == 1 ? $"Opening {added[0].FileName}" : $"Opening {added.Count} PDFs");
        using var throttle = new SemaphoreSlim(MaxConcurrentFileReads);

        // Continuations resume on the UI thread, so item updates are safe.
        await Task.WhenAll(added.Select(item => LoadOneAsync(item, throttle, cancellationToken)));

        return new ImportResult(added.Count, duplicates, skipped);
    }

    private async Task LoadOneAsync(DocumentItemViewModel item, SemaphoreSlim throttle, CancellationToken cancellationToken)
    {
        try
        {
            await throttle.WaitAsync(cancellationToken);
            try
            {
                var info = await engine.OpenAsync(item.FilePath, cancellationToken);
                item.PageCount = info.PageCount;
                item.State = DocumentLoadState.Ready;
            }
            finally
            {
                throttle.Release();
            }
        }
        catch (OperationCanceledException)
        {
            // Cancelled imports are removed rather than left half-loaded.
            Documents.Remove(item);
        }
        catch (PdfOpenException error)
        {
            item.ErrorMessage = error.Message;
            item.State = DocumentLoadState.Failed;
        }
        catch (Exception error)
        {
            crashLog.Write($"Opening {item.FilePath} failed", error);
            item.ErrorMessage = "Unexpected error while opening this PDF. Details were saved to crash.log.";
            item.State = DocumentLoadState.Failed;
        }
    }

    /// <summary>Closes documents and releases their cached previews. Original files are untouched.</summary>
    public void Close(IEnumerable<DocumentItemViewModel> items)
    {
        foreach (var item in items.ToList())
        {
            Documents.Remove(item);
            if (ReferenceEquals(ActiveDocument, item))
            {
                // Clearing the active document clears the preview immediately,
                // so a closed PDF can never remain visible.
                ActiveDocument = null;
            }

            _ = ForgetAsync(item.FilePath);
        }
    }

    private async Task ForgetAsync(string path)
    {
        try
        {
            await previews.ForgetDocumentAsync(path);
        }
        catch (Exception error)
        {
            crashLog.Write($"Releasing {path} failed", error);
        }
    }

    private static bool SamePath(string a, string b) =>
        string.Equals(a, b, OperatingSystem.IsWindows() || OperatingSystem.IsMacOS()
            ? StringComparison.OrdinalIgnoreCase
            : StringComparison.Ordinal);
}
