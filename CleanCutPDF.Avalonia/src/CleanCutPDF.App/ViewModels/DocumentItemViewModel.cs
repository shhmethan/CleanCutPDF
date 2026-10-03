using CleanCutPDF.Core.Models;
using CleanCutPDF.Core.Pdf;
using CommunityToolkit.Mvvm.ComponentModel;

namespace CleanCutPDF.App.ViewModels;

public enum DocumentLoadState
{
    Loading,
    Ready,
    Failed
}

public enum DetectionState
{
    NotStarted,
    Running,
    Done,
    Failed
}

/// <summary>One imported PDF: shown in the Inbox and edited in Split &amp; Rename.</summary>
public sealed partial class DocumentItemViewModel(string filePath, string workspace) : ObservableObject, IPreviewDocument
{
    public string FilePath { get; } = filePath;
    public string FileName { get; } = Path.GetFileName(filePath);

    [ObservableProperty]
    public partial string FolderId { get; set; } = Core.Sessions.SessionFolder.InboxId;

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(DisplayText))]
    public partial string Workspace { get; set; } = workspace;

    [ObservableProperty]
    public partial string ClientName { get; set; } = "";

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(StatusText), nameof(IsReady), nameof(IsFailed), nameof(IsLoading), nameof(IsBusy))]
    public partial DocumentLoadState State { get; set; } = DocumentLoadState.Loading;

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(StatusText))]
    public partial int PageCount { get; set; }

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(StatusText))]
    public partial string? ErrorMessage { get; set; }

    public FileSignature? Signature { get; set; }

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(StatusText), nameof(IsBusy), nameof(IsDetected), nameof(DetectionPercent))]
    public partial DetectionState Detection { get; set; } = DetectionState.NotStarted;

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(StatusText), nameof(DetectionPercent))]
    public partial int PagesScanned { get; set; }

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(StatusText), nameof(PartCount))]
    public partial IReadOnlyList<PageRange> Ranges { get; set; } = [];

    public IReadOnlyList<int> MarkerPages { get; set; } = [];

    /// <summary>Workspace name → values per Part, so switching workspaces back and forth keeps what was typed.</summary>
    public Dictionary<string, List<Dictionary<string, string>>> WorkspaceData { get; set; } = new();

    /// <summary>Cancels split detection when the document is closed.</summary>
    public CancellationTokenSource? DetectionCts { get; set; }

    /// <summary>Completing this moves a queued detection to the front.</summary>
    public TaskCompletionSource? DetectionPromotion { get; set; }

    /// <summary>A multi-page PDF that came out as a single Part because no SPLIT HERE pages were found.</summary>
    public bool NoMarkersFound =>
        Detection == DetectionState.Done && MarkerPages.Count == 0 && Ranges.Count <= 1 && PageCount > 1;

    public int PartCount => Ranges.Count;
    public bool IsReady => State == DocumentLoadState.Ready;
    public bool IsFailed => State == DocumentLoadState.Failed;
    public bool IsLoading => State == DocumentLoadState.Loading;
    public bool IsDetected => Detection == DetectionState.Done;
    public bool IsBusy => IsLoading || Detection == DetectionState.Running;
    public double DetectionPercent => PageCount == 0 ? 0 : 100.0 * PagesScanned / PageCount;

    /// <summary>Matches the 1.x explorer label: "file.pdf  [Workspace]".</summary>
    public string DisplayText => $"{FileName}  [{Workspace}]";

    public string StatusText
    {
        get
        {
            if (State == DocumentLoadState.Loading)
            {
                return "Loading…";
            }

            if (State == DocumentLoadState.Failed)
            {
                return ErrorMessage ?? "Could not be opened";
            }

            var pages = PageCount == 1 ? "1 page" : $"{PageCount} pages";
            return Detection switch
            {
                DetectionState.Running => $"{pages} · finding SPLIT HERE pages… {PagesScanned}/{PageCount}",
                DetectionState.Done => $"{pages} · {(PartCount == 1 ? "1 part" : $"{PartCount} parts")}" +
                                       (NoMarkersFound ? " (no SPLIT HERE pages)" : ""),
                DetectionState.Failed => $"{pages} · split detection failed; treated as one part",
                _ => pages
            };
        }
    }

    // Used as the accessible name read by screen readers.
    public override string ToString() => $"{DisplayText}, {StatusText}";
}
