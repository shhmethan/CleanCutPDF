using CleanCutPDF.App.Services;
using CleanCutPDF.Core;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Services;
using CommunityToolkit.Mvvm.ComponentModel;

namespace CleanCutPDF.App.ViewModels;

public sealed record NavigationItem(AppPage Page, string Title, string Glyph, ObservableObject Content)
{
    // Used as the accessible name read by screen readers.
    public override string ToString() => Title;
}

/// <summary>Application shell: navigation, status bar, and startup.</summary>
public sealed partial class MainWindowViewModel : ObservableObject
{
    private readonly ISettingsService _settings;
    private readonly SettingsViewModel _settingsPage;
    private readonly InboxViewModel _inbox;
    private readonly CrashLog _crashLog;

    public MainWindowViewModel(
        InboxViewModel inbox,
        SplitRenameViewModel splitRename,
        RenameOnlyViewModel renameOnly,
        SettingsViewModel settingsPage,
        NavigationService navigation,
        ActivityService activity,
        ISettingsService settings,
        ThemeService themeService,
        LicenseViewModel license,
        UpdatesViewModel updates,
        CrashLog crashLog)
    {
        _ = themeService; // Constructed here so it subscribes to settings changes.
        _inbox = inbox;
        _settingsPage = settingsPage;
        _settings = settings;
        _crashLog = crashLog;
        Activity = activity;
        License = license;
        Updates = updates;
        License.StateChanged += (_, _) => OnPropertyChanged(nameof(Title));

        NavigationItems =
        [
            new(AppPage.Inbox, "Inbox", "📥", inbox),
            new(AppPage.SplitRename, "Split & Rename", "✂", splitRename),
            new(AppPage.RenameOnly, "Rename Only", "📝", renameOnly),
            new(AppPage.Settings, "Settings", "⚙", settingsPage)
        ];
        SelectedNavigationItem = NavigationItems[0];

        navigation.NavigationRequested += (_, page) =>
            SelectedNavigationItem = NavigationItems.First(item => item.Page == page);
    }

    public string Title => License.State.AllowsUse && License.LicensedTo is { } company
        ? $"{AppInfo.ProductName} {AppInfo.Version} (preview) – Licensed to {company}"
        : $"{AppInfo.ProductName} {AppInfo.Version} (preview)";

    public LicenseViewModel License { get; }

    public UpdatesViewModel Updates { get; }

    public IReadOnlyList<NavigationItem> NavigationItems { get; }

    public ActivityService Activity { get; }

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(CurrentPage))]
    public partial NavigationItem? SelectedNavigationItem { get; set; }

    public ObservableObject? CurrentPage => SelectedNavigationItem?.Content;

    /// <summary>Runs after the window is shown so startup work never delays the first frame.</summary>
    /// <param name="startupFiles">PDFs passed on the command line ("Open with CleanCutPDF").</param>
    public async Task InitializeAsync(IReadOnlyList<string> startupFiles)
    {
        try
        {
            using (Activity.Begin("Loading settings"))
            {
                await _settings.LoadAsync();
            }

            // The license is read locally (no network); a due weekly license
            // recheck and the every-launch update check run in the background.
            await License.InitializeAsync();
            _ = Updates.InitializeAsync();

            var legacy = _settingsPage.LoadLegacyStatusAsync();
            if (startupFiles.Count > 0)
            {
                await _inbox.ImportAsync(startupFiles);
            }

            await legacy;
        }
        catch (Exception error)
        {
            _crashLog.Write("Startup initialization failed", error);
            Activity.Report("Some settings could not be loaded; defaults are in use.");
        }
    }

    /// <summary>Files dropped anywhere on the window go to the Inbox.</summary>
    public async Task ImportDroppedFilesAsync(IReadOnlyList<string> paths)
    {
        if (License.IsLocked)
        {
            return;
        }

        SelectedNavigationItem = NavigationItems.First(item => item.Page == AppPage.Inbox);
        await _inbox.ImportAsync(paths);
    }
}
