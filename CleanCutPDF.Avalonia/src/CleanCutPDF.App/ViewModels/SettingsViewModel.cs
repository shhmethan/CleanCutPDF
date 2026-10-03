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

public sealed record AccentOption(AppAccent Accent, string Label)
{
    public override string ToString() => Label;
}

/// <param name="Family">Stored font family; empty for the built-in default.</param>
public sealed record FontOption(string Family, string Label)
{
    public override string ToString() => Label;
}

/// <summary>Settings page: appearance, export, behavior, shortcuts, import, diagnostics, license, updates, reset.</summary>
public sealed partial class SettingsViewModel : ObservableObject
{
    private readonly ISettingsService _settings;
    private readonly IDialogService _dialogs;
    private readonly IShellService _shell;
    private readonly LegacyDataLocator _legacy;
    private readonly SettingsReset _reset;
    private readonly ActivityService _activity;
    private readonly CrashLog _crashLog;
    private bool _syncing;

    public SettingsViewModel(ISettingsService settings, IDialogService dialogs, IShellService shell,
        LegacyDataLocator legacy, AppPaths paths, LicenseViewModel license, UpdatesViewModel updates, AppLog log,
        FolderShortcutsViewModel shortcuts, LegacyImportViewModel legacyImport, KeybindsViewModel keybinds,
        SettingsReset reset, ActivityService activity, CrashLog crashLog)
    {
        Keybinds = keybinds;
        _reset = reset;
        _activity = activity;
        _crashLog = crashLog;
        FontOptions = [new FontOption("", "Inter (default)"), .. ThemeService.InstalledFontChoices().Select(f => new FontOption(f, f))];
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

    public IReadOnlyList<AccentOption> AccentOptions { get; } =
    [
        new(AppAccent.Blue, "Blue"),
        new(AppAccent.Green, "Green"),
        new(AppAccent.Pink, "Pink")
    ];

    public IReadOnlyList<FontOption> FontOptions { get; }

    public IReadOnlyList<int> FontSizes { get; } =
        Enumerable.Range(AppSettings.MinFontSize, AppSettings.MaxFontSize - AppSettings.MinFontSize + 1).ToList();

    [ObservableProperty]
    public partial AccentOption? SelectedAccent { get; set; }

    partial void OnSelectedAccentChanged(AccentOption? value)
    {
        if (!_syncing && value is not null)
        {
            _settings.Update(s => s.Accent = value.Accent);
        }
    }

    [ObservableProperty]
    public partial FontOption? SelectedFont { get; set; }

    partial void OnSelectedFontChanged(FontOption? value)
    {
        if (!_syncing && value is not null)
        {
            _settings.Update(s => s.FontFamily = value.Family);
        }
    }

    [ObservableProperty]
    public partial int SelectedFontSize { get; set; } = AppSettings.DefaultFontSize;

    partial void OnSelectedFontSizeChanged(int value)
    {
        if (!_syncing && value >= AppSettings.MinFontSize)
        {
            _settings.Update(s => s.FontSize = AppSettings.ClampFontSize(value));
        }
    }

    [RelayCommand]
    private void ResetFont() => _settings.Update(s =>
    {
        s.FontFamily = "";
        s.FontSize = AppSettings.DefaultFontSize;
    });

    /// <summary>
    /// 1.x Reset Settings: type a short code, then settings, workspaces, and
    /// custom fields return to the defaults. Applied live (1.x restarted).
    /// </summary>
    [RelayCommand]
    private async Task ResetSettingsAsync()
    {
        Keybinds.CancelCapture();
        var code = SettingsReset.NewCode();
        if (!await _dialogs.ConfirmWithCodeAsync("Reset Settings",
                "This resets every setting, all workspaces, and all custom fields to the defaults.\n\n" +
                "Your license, export history, open PDFs, diagnostic logs, and keyboard shortcuts are kept. " +
                "The current settings are backed up first.\n\nTo continue, type this code:",
                code, entered => SettingsReset.CodeMatches(code, entered), "Reset Settings"))
        {
            return;
        }

        try
        {
            string backup;
            using (_activity.Begin("Resetting settings"))
            {
                backup = await _reset.ResetAsync();
            }

            await _dialogs.ShowMessageAsync("Reset Settings",
                $"Settings, workspaces, and custom fields were reset to the defaults.\n\nA backup of the previous files is in:\n{backup}");
        }
        catch (Exception error)
        {
            _crashLog.Write("Reset Settings failed", error);
            await _dialogs.ShowMessageAsync("Reset Settings",
                $"The settings could not be reset.\n\n{error.Message}\n\nDetails were saved to the diagnostic log.");
        }
    }

    public KeybindsViewModel Keybinds { get; }

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
            SelectedAccent = AccentOptions.FirstOrDefault(o => o.Accent == current.Accent) ?? AccentOptions[0];
            SelectedFont = FontOptions.FirstOrDefault(o => string.Equals(o.Family, current.FontFamily, StringComparison.OrdinalIgnoreCase))
                           ?? FontOptions[0];
            SelectedFontSize = AppSettings.ClampFontSize(current.FontSize);
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
