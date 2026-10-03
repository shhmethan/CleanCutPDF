using CleanCutPDF.App.Services;
using CleanCutPDF.Core;
using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Models;
using CleanCutPDF.Core.Services;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace CleanCutPDF.App.ViewModels;

public sealed record ThemeOption(AppThemeMode Mode, string Label)
{
    public override string ToString() => Label;
}

/// <summary>Settings page. Phase 1: theme, export folder, version, and data locations.</summary>
public sealed partial class SettingsViewModel : ObservableObject
{
    private readonly ISettingsService _settings;
    private readonly IDialogService _dialogs;
    private readonly IShellService _shell;
    private readonly LegacyDataLocator _legacy;
    private bool _syncing;

    public SettingsViewModel(ISettingsService settings, IDialogService dialogs, IShellService shell,
        LegacyDataLocator legacy, AppPaths paths, LicenseViewModel license, UpdatesViewModel updates, AppLog log,
        FolderShortcutsViewModel shortcuts, LegacyImportViewModel legacyImport)
    {
        Shortcuts = shortcuts;
        LegacyImport = legacyImport;
        LogsFolder = log.Directory;
        License = license;
        Updates = updates;
        _settings = settings;
        _dialogs = dialogs;
        _shell = shell;
        _legacy = legacy;
        DataFolder = paths.DataDirectory;
        _settings.Changed += (_, current) => SyncFrom(current);
        SyncFrom(_settings.Current);
    }

    public IReadOnlyList<ThemeOption> ThemeOptions { get; } =
    [
        new(AppThemeMode.Light, "Light"),
        new(AppThemeMode.Dark, "Dark"),
        new(AppThemeMode.System, "Match system")
    ];

    public FolderShortcutsViewModel Shortcuts { get; }

    public LegacyImportViewModel LegacyImport { get; }

    public LicenseViewModel License { get; }

    public UpdatesViewModel Updates { get; }

    public string VersionText => $"{AppInfo.ProductName} {AppInfo.Version} (preview, modeled on v{AppInfo.ReferenceLegacyVersion})";

    public string DataFolder { get; }

    public string LogsFolder { get; }

    [ObservableProperty]
    public partial bool RemoveBlankPages { get; set; }

    partial void OnRemoveBlankPagesChanged(bool value)
    {
        if (!_syncing)
        {
            _settings.Update(s => s.RemoveBlankPages = value);
        }
    }

    [ObservableProperty]
    public partial bool WarnOnFutureDates { get; set; }

    partial void OnWarnOnFutureDatesChanged(bool value)
    {
        if (!_syncing)
        {
            _settings.Update(s => s.WarnOnFutureDates = value);
        }
    }

    [ObservableProperty]
    public partial bool WarnWhenNoSplitMarkers { get; set; }

    partial void OnWarnWhenNoSplitMarkersChanged(bool value)
    {
        if (!_syncing)
        {
            _settings.Update(s => s.WarnWhenNoSplitMarkers = value);
        }
    }

    [ObservableProperty]
    public partial bool AutoRestoreSession { get; set; }

    partial void OnAutoRestoreSessionChanged(bool value)
    {
        if (!_syncing)
        {
            _settings.Update(s => s.AutoRestoreSession = value);
        }
    }

    [ObservableProperty]
    public partial bool MakeClientFolder { get; set; }

    partial void OnMakeClientFolderChanged(bool value)
    {
        if (!_syncing)
        {
            _settings.Update(s => s.MakeClientFolder = value);
        }
    }

    [ObservableProperty]
    public partial bool VerboseLogging { get; set; }

    partial void OnVerboseLoggingChanged(bool value)
    {
        if (!_syncing)
        {
            _settings.Update(s => s.VerboseLogging = value);
        }
    }

    [RelayCommand]
    private async Task OpenLogsFolderAsync()
    {
        Directory.CreateDirectory(LogsFolder);
        var error = _shell.OpenFolder(LogsFolder, "Logs folder");
        if (error is not null)
        {
            await _dialogs.ShowMessageAsync("Open Folder", error);
        }
    }

    [ObservableProperty]
    public partial ThemeOption? SelectedTheme { get; set; }

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(ExportFolderDisplay))]
    [NotifyCanExecuteChangedFor(nameof(OpenExportFolderCommand))]
    public partial string ExportFolder { get; private set; } = string.Empty;

    public string ExportFolderDisplay => string.IsNullOrWhiteSpace(ExportFolder) ? "Not set" : ExportFolder;

    [ObservableProperty]
    public partial string LegacyStatus { get; private set; } = "Checking for CleanCutPDF 1.x data…";

    public async Task LoadLegacyStatusAsync()
    {
        var summary = await _legacy.InspectAsync();
        LegacyStatus = summary.Found
            ? $"Found CleanCutPDF 1.x data in {summary.Directory} " +
              $"(settings: {(summary.HasSettings ? "yes" : "no")}, sessions: {(summary.HasSessions ? "yes" : "no")}, " +
              $"export log: {(summary.HasExportLog ? $"{summary.ExportLogBytes / 1024:N0} KB" : "no")}). " +
              "Importing only reads it; it is never changed."
            : "No CleanCutPDF 1.x data was found on this computer.";
    }

    partial void OnSelectedThemeChanged(ThemeOption? value)
    {
        if (!_syncing && value is not null)
        {
            _settings.Update(s => s.Theme = value.Mode);
        }
    }

    [RelayCommand]
    private async Task BrowseExportFolderAsync()
    {
        var folder = await _dialogs.PickFolderAsync("Select Export Folder");
        if (!string.IsNullOrWhiteSpace(folder))
        {
            _settings.Update(s => s.ExportFolder = folder);
        }
    }

    [RelayCommand(CanExecute = nameof(HasExportFolder))]
    private async Task OpenExportFolderAsync()
    {
        var error = _shell.OpenFolder(ExportFolder, "Default Export Folder");
        if (error is not null)
        {
            await _dialogs.ShowMessageAsync("Open Folder", error);
        }
    }

    private bool HasExportFolder() => !string.IsNullOrWhiteSpace(ExportFolder);

    [RelayCommand]
    private async Task OpenDataFolderAsync()
    {
        Directory.CreateDirectory(DataFolder);
        var error = _shell.OpenFolder(DataFolder, "Data folder");
        if (error is not null)
        {
            await _dialogs.ShowMessageAsync("Open Folder", error);
        }
    }

    private void SyncFrom(AppSettings current)
    {
        _syncing = true;
        try
        {
            SelectedTheme = ThemeOptions.FirstOrDefault(o => o.Mode == current.Theme) ?? ThemeOptions[0];
            ExportFolder = current.ExportFolder;
            VerboseLogging = current.VerboseLogging;
            RemoveBlankPages = current.RemoveBlankPages;
            WarnOnFutureDates = current.WarnOnFutureDates;
            WarnWhenNoSplitMarkers = current.WarnWhenNoSplitMarkers;
            AutoRestoreSession = current.AutoRestoreSession;
            MakeClientFolder = current.MakeClientFolder;
        }
        finally
        {
            _syncing = false;
        }
    }
}
