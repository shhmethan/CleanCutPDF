using CleanCutPDF.App.Services;
using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Services;
using CleanCutPDF.Core.Updates;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace CleanCutPDF.App.ViewModels;

/// <summary>
/// Update banner on the main window and the Updates section in Settings.
/// Checks run in the background on every launch; nothing is downloaded or
/// installed until the user chooses Install Update. An installed copy then
/// updates itself (download, verify, close, install, reopen); a copy run from
/// a build folder only offers the download link.
/// </summary>
public sealed partial class UpdatesViewModel : ObservableObject
{
    private readonly UpdateService _updates;
    private readonly ISettingsService _settings;
    private readonly IShellService _shell;
    private readonly IDialogService _dialogs;
    private readonly ActivityService _activity;
    private readonly CrashLog _crashLog;
    private readonly AppLog _log;
    private readonly UpdateInstaller _installer;
    private readonly AppLifetimeService _lifetime;
    private CancellationTokenSource? _installCts;
    private UpdatePackage? _package;
    private bool _syncing;

    public UpdatesViewModel(UpdateService updates, ISettingsService settings, IShellService shell,
        IDialogService dialogs, ActivityService activity, CrashLog crashLog, AppLog log,
        UpdateInstaller installer, AppLifetimeService lifetime)
    {
        _installer = installer;
        _lifetime = lifetime;
        _log = log;
        _updates = updates;
        _settings = settings;
        _shell = shell;
        _dialogs = dialogs;
        _activity = activity;
        _crashLog = crashLog;
        _settings.Changed += (_, current) =>
        {
            _syncing = true;
            CheckAutomatically = current.CheckUpdatesOnStartup;
            _syncing = false;
            OnPropertyChanged(nameof(LastCheckedText));
        };
    }

    public string CurrentVersion => _updates.CurrentVersion.ToString();

    [ObservableProperty]
    public partial bool IsBannerVisible { get; private set; }

    [ObservableProperty]
    public partial string BannerText { get; private set; } = "";

    [ObservableProperty]
    public partial IReadOnlyList<string> BannerNotes { get; private set; } = [];

    [ObservableProperty]
    public partial IReadOnlyList<ReleaseNotes> ReleaseNotes { get; private set; } = [];

    [ObservableProperty]
    public partial string? StatusText { get; private set; }

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(CheckNowCommand))]
    public partial bool IsChecking { get; private set; }

    [ObservableProperty]
    public partial bool CheckAutomatically { get; set; } = true;

    public string LastCheckedText => _updates.LastCheckedUtc is { } when
        ? when.ToLocalTime().ToString("MMMM d, yyyy h:mm tt")
        : "Never";

    private Uri? _downloadPage;

    /// <summary>Shows cached results immediately, then checks online in the background.</summary>
    public async Task InitializeAsync()
    {
        try
        {
            await _updates.LoadCacheAsync();
            ReleaseNotes = _updates.AllReleaseNotes();
            if (_updates.CachedResult() is { Outcome: UpdateCheckOutcome.UpdateAvailable } cached)
            {
                ShowBanner(cached);
            }

            if (_updates.IsAutomaticCheckDue)
            {
                _ = CheckAsync(userInitiated: false);
            }
        }
        catch (Exception error)
        {
            _crashLog.Write("Update initialization failed", error);
        }
    }

    [RelayCommand(CanExecute = nameof(CanCheck))]
    private Task CheckNowAsync() => CheckAsync(userInitiated: true);

    private bool CanCheck() => !IsChecking;

    [RelayCommand]
    private async Task OpenDownloadAsync()
    {
        var error = _shell.OpenUrl(_downloadPage ?? RemoteEndpoints.ReleasesPage);
        if (error is not null)
        {
            await _dialogs.ShowMessageAsync("Open Download Page", error);
        }
    }

    [RelayCommand]
    private void DismissBanner() => IsBannerVisible = false;

    // ───── Installing ─────

    /// <summary>True when this copy can install the available update itself.</summary>
    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(ShowInstall), nameof(ShowDownloadLink))]
    public partial bool CanInstallUpdate { get; private set; }

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(ShowInstall))]
    [NotifyCanExecuteChangedFor(nameof(InstallUpdateCommand))]
    public partial bool IsInstalling { get; private set; }

    [ObservableProperty]
    public partial string InstallStatus { get; private set; } = "";

    [ObservableProperty]
    public partial int InstallPercent { get; private set; }

    public bool ShowInstall => CanInstallUpdate && !IsInstalling;

    public bool ShowDownloadLink => !CanInstallUpdate;

    /// <summary>Download, verify, then hand over to the installer and close.</summary>
    [RelayCommand(CanExecute = nameof(CanStartInstall))]
    private async Task InstallUpdateAsync()
    {
        if (_package is not { } package ||
            !await _dialogs.ConfirmAsync("Install Update",
                $"CleanCutPDF {package.Version} will be downloaded and installed.\n\n" +
                "CleanCutPDF closes for a moment and reopens by itself. Your open PDFs and everything typed into them are saved first.",
                "Install Update"))
        {
            return;
        }

        IsInstalling = true;
        InstallPercent = 0;
        InstallStatus = $"Downloading CleanCutPDF {package.Version}…";
        _installCts = new CancellationTokenSource();
        try
        {
            string installer;
            using (_activity.Begin($"Downloading CleanCutPDF {package.Version}"))
            {
                var progress = new Progress<DownloadProgress>(p =>
                {
                    if (p.Percent is { } percent)
                    {
                        InstallPercent = percent;
                        InstallStatus = $"Downloading CleanCutPDF {package.Version}… {percent}%";
                    }
                });
                installer = await _installer.DownloadAsync(package, progress, _installCts.Token);
            }

            InstallPercent = 100;
            InstallStatus = "Installing… CleanCutPDF will close and reopen.";
            _installer.Launch(installer);
            _lifetime.Quit(); // Saves everything, then exits so the installer can replace the files.
        }
        catch (OperationCanceledException)
        {
            InstallStatus = "";
            IsInstalling = false;
            _activity.Report("The update was cancelled.");
        }
        catch (Exception error)
        {
            _crashLog.Write("Installing the update failed", error);
            InstallStatus = "";
            IsInstalling = false;
            await _dialogs.ShowMessageAsync("Install Update",
                $"The update could not be installed.\n\n{error.Message}\n\nNothing was changed. You can try again later.");
        }
    }

    private bool CanStartInstall() => !IsInstalling;

    [RelayCommand]
    private void CancelInstall() => _installCts?.Cancel();

    partial void OnCheckAutomaticallyChanged(bool value)
    {
        if (!_syncing)
        {
            _settings.Update(s => s.CheckUpdatesOnStartup = value);
        }
    }

    private async Task CheckAsync(bool userInitiated)
    {
        IsChecking = true;
        StatusText = "Checking for updates…";
        try
        {
            using var _ = _activity.Begin("Checking for updates");
            var result = await _updates.CheckAsync();
            _log.Info("Updates", $"{(userInitiated ? "Manual" : "Launch")} check: {result.Outcome}" +
                                 (result.LatestVersion is null ? "" : $" (latest {result.LatestVersion})"));
            StatusText = result.Message;
            ReleaseNotes = _updates.AllReleaseNotes();
            OnPropertyChanged(nameof(LastCheckedText));

            if (result.Outcome == UpdateCheckOutcome.UpdateAvailable)
            {
                ShowBanner(result);
            }
            else if (userInitiated)
            {
                _activity.Report(result.Message);
            }
        }
        catch (Exception error)
        {
            _crashLog.Write("Update check failed", error);
            StatusText = "The update check failed. Details were saved to crash.log.";
        }
        finally
        {
            IsChecking = false;
        }
    }

    private void ShowBanner(UpdateCheckResult result)
    {
        _package = result.Package;
        CanInstallUpdate = result.Package is not null && _installer.CanInstall(_updates.CachedManifest);
        _downloadPage = result.DownloadPage;
        BannerText = result.Message;
        BannerNotes = result.Notes;
        IsBannerVisible = true;
    }
}
