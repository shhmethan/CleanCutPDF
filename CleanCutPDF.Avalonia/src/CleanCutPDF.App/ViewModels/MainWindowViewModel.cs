using CleanCutPDF.App.Services;
using CleanCutPDF.Core;
using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Services;
using CleanCutPDF.Core.Shortcuts;
using CleanCutPDF.Core.Workspaces;
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
    private readonly AppLog? _log;
    private readonly WorkspaceStore _workspaces;
    private readonly DocumentStore _documents;
    private readonly RenameOnlyViewModel _renameOnly;
    private readonly QuickSplitViewModel _quickSplit;
    private readonly ToolsService _tools;

    /// <summary>Ctrl+Alt+D (as in 1.x).</summary>
    public void OpenDebugConsole() => _tools.OpenDebugConsole();
    private readonly ClientSuggestions _clientSuggestions;
    private readonly KeybindsViewModel _keybinds;
    private readonly AppLifetimeService _lifetime;
    private readonly IDialogService _dialogs;
    private readonly SplitRenameViewModel _splitRename;
    private readonly LogsViewModel _logs;
    private readonly NavigationService _navigation;
    private bool _shortcutRunning;

    /// <summary>Asks the window to put the keyboard focus in a named control (or its first input).</summary>
    public event EventHandler<string>? FocusRequested;

    /// <summary>Asks the window to paste the clipboard into the focused text box.</summary>
    public event EventHandler? PasteRequested;

    /// <summary>The shortcut action a key press should run, or null.</summary>
    public string? MatchShortcut(string gesture) => License.IsLocked ? null : _keybinds.Match(gesture);

    /// <summary>Runs a keyboard shortcut (ids are in <see cref="ShortcutCatalog"/>).</summary>
    public async Task RunShortcutAsync(string id)
    {
        if (_shortcutRunning || License.IsLocked)
        {
            return; // A held key must not start the same action twice.
        }

        _shortcutRunning = true;
        try
        {
            _log?.Debug("Shortcut", id);
            var page = SelectedNavigationItem?.Page;
            switch (id)
            {
                case ShortcutCatalog.OpenPdf:
                    _navigation.NavigateTo(AppPage.Inbox);
                    await _inbox.OpenPdfsCommand.ExecuteAsync(null);
                    break;
                case ShortcutCatalog.ClosePdf:
                    // 1.x asked first, so one stray key press cannot discard typed values.
                    if (page == AppPage.SplitRename && _splitRename.Document is { } document
                        && _splitRename.CloseDocumentCommand.CanExecute(null)
                        && await _dialogs.ConfirmAsync("Close PDF", $"Close “{document.FileName}”?", "Close"))
                    {
                        _splitRename.CloseDocumentCommand.Execute(null);
                    }

                    break;
                case ShortcutCatalog.Export:
                    if (page == AppPage.RenameOnly && _renameOnly.RenameCommand.CanExecute(null))
                    {
                        await _renameOnly.RenameCommand.ExecuteAsync(null);
                    }
                    else if (page == AppPage.SplitRename && _splitRename.ExportCommand.CanExecute(null))
                    {
                        await _splitRename.ExportCommand.ExecuteAsync(null);
                    }

                    break;
                case ShortcutCatalog.ResetForm:
                    if (page == AppPage.SplitRename && _splitRename.ResetFormCommand.CanExecute(null))
                    {
                        await _splitRename.ResetFormCommand.ExecuteAsync(null);
                    }

                    break;
                case ShortcutCatalog.Quit:
                    _lifetime.Quit();
                    break;
                case ShortcutCatalog.SearchLogs:
                    _navigation.NavigateTo(AppPage.Logs);
                    FocusRequested?.Invoke(this, "LogSearchBox");
                    break;
                case ShortcutCatalog.UndoLastExport:
                    await _tools.UndoLastExportAsync();
                    break;
                case ShortcutCatalog.PasteClipboard:
                    PasteRequested?.Invoke(this, EventArgs.Empty);
                    break;
                case ShortcutCatalog.ClearLog:
                    _navigation.NavigateTo(AppPage.Logs);
                    await _logs.EnsureLoadedAsync();
                    await _logs.ClearLogCommand.ExecuteAsync(null);
                    break;
                case ShortcutCatalog.FocusClientName when _splitRename.HasDocument:
                    _navigation.NavigateTo(AppPage.SplitRename);
                    FocusRequested?.Invoke(this, "ClientNameBox");
                    break;
                case ShortcutCatalog.FocusFirstPart when _splitRename.HasDocument:
                    _navigation.NavigateTo(AppPage.SplitRename);
                    FocusRequested?.Invoke(this, "PartsList");
                    break;
                case ShortcutCatalog.SelectExportFolder:
                    await _settingsPage.BrowseExportFolderCommand.ExecuteAsync(null);
                    break;
            }
        }
        catch (Exception error)
        {
            _crashLog.Write($"Keyboard shortcut {id} failed", error);
            Activity.Report("That shortcut could not be completed; details are in the diagnostic log.");
        }
        finally
        {
            _shortcutRunning = false;
        }
    }

    public MainWindowViewModel(
        InboxViewModel inbox,
        SplitRenameViewModel splitRename,
        RenameOnlyViewModel renameOnly,
        QuickSplitViewModel quickSplit,
        LogsViewModel logs,
        ToolsService tools,
        WorkspacesViewModel workspacesPage,
        ClientSuggestions clientSuggestions,
        SettingsViewModel settingsPage,
        NavigationService navigation,
        ActivityService activity,
        ISettingsService settings,
        ThemeService themeService,
        LicenseViewModel license,
        UpdatesViewModel updates,
        CrashLog crashLog,
        AppLog log,
        WorkspaceStore workspaces,
        DocumentStore documents,
        KeybindsViewModel keybinds,
        AppLifetimeService lifetime,
        IDialogService dialogs)
    {
        _keybinds = keybinds;
        _lifetime = lifetime;
        _dialogs = dialogs;
        _splitRename = splitRename;
        _logs = logs;
        _navigation = navigation;
        _log = log;
        _workspaces = workspaces;
        _documents = documents;
        _renameOnly = renameOnly;
        _quickSplit = quickSplit;
        _tools = tools;
        _clientSuggestions = clientSuggestions;
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
            new(AppPage.QuickSplit, "Quick Split", "⚡", quickSplit),
            new(AppPage.Logs, "Logs", "📜", logs),
            new(AppPage.Workspaces, "Workspaces", "🧩", workspacesPage),
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

    partial void OnSelectedNavigationItemChanged(NavigationItem? value)
    {
        if (value is not null)
        {
            _log?.Debug("Navigation", value.Title);
        }
    }

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
            await _workspaces.LoadAsync();
            _ = _clientSuggestions.RefreshAsync();
            if (_settings.Current.AutoRestoreSession)
            {
                using (Activity.Begin("Restoring previous session"))
                {
                    await _documents.RestoreAsync(_workspaces.Catalog.WorkspaceNames.ToHashSet());
                }
            }

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

        // Dropping onto Rename Only or Quick Split adds the files there instead of the Inbox.
        switch (SelectedNavigationItem?.Page)
        {
            case AppPage.RenameOnly:
                await _renameOnly.AddFilesAsync(paths);
                return;
            case AppPage.QuickSplit:
                await _quickSplit.SplitAsync(paths);
                return;
        }

        SelectedNavigationItem = NavigationItems.First(item => item.Page == AppPage.Inbox);
        await _inbox.ImportAsync(paths);
    }
}
