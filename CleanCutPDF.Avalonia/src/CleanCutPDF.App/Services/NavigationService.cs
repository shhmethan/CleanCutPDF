namespace CleanCutPDF.App.Services;

public enum AppPage
{
    Inbox,
    SplitRename,
    RenameOnly,
    QuickSplit,
    Logs,
    Workspaces,
    Help,
    Settings
}

/// <summary>Lets pages request navigation without referencing the main window.</summary>
public sealed class NavigationService
{
    public event EventHandler<AppPage>? NavigationRequested;

    public void NavigateTo(AppPage page) => NavigationRequested?.Invoke(this, page);
}
