using CommunityToolkit.Mvvm.ComponentModel;

namespace CleanCutPDF.App.ViewModels;

public enum DocumentLoadState
{
    Loading,
    Ready,
    Failed
}

/// <summary>One imported PDF as shown in the Inbox and opened in the editor.</summary>
public sealed partial class DocumentItemViewModel(string filePath, string workspace) : ObservableObject
{
    public string FilePath { get; } = filePath;
    public string FileName { get; } = Path.GetFileName(filePath);
    public string FolderName { get; } = "Inbox";

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(DisplayText))]
    public partial string Workspace { get; set; } = workspace;

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(StatusText), nameof(IsReady), nameof(IsFailed), nameof(IsLoading))]
    public partial DocumentLoadState State { get; set; } = DocumentLoadState.Loading;

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(StatusText))]
    public partial int PageCount { get; set; }

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(StatusText))]
    public partial string? ErrorMessage { get; set; }

    /// <summary>Matches the Python explorer label: "file.pdf  [Workspace]".</summary>
    public string DisplayText => $"{FileName}  [{Workspace}]";

    public bool IsReady => State == DocumentLoadState.Ready;
    public bool IsFailed => State == DocumentLoadState.Failed;
    public bool IsLoading => State == DocumentLoadState.Loading;

    public string StatusText => State switch
    {
        DocumentLoadState.Loading => "Loading…",
        DocumentLoadState.Ready => PageCount == 1 ? "1 page" : $"{PageCount} pages",
        _ => ErrorMessage ?? "Could not be opened"
    };

    // Used as the accessible name read by screen readers.
    public override string ToString() => $"{DisplayText}, {StatusText}";
}
