using CleanCutPDF.App.Services;
using CleanCutPDF.Core;
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
        LegacyDataLocator legacy, AppPaths paths, LicenseViewModel license, UpdatesViewModel updates)
    {
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

    public LicenseViewModel License { get; }

    public UpdatesViewModel Updates { get; }

    public string VersionText => $"{AppInfo.ProductName} {AppInfo.Version} (preview, modeled on v{AppInfo.ReferenceLegacyVersion})";

    public string DataFolder { get; }

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
              "It is left untouched; a read-only import is planned for Phase 3."
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
        }
        finally
        {
            _syncing = false;
        }
    }
}
