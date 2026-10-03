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
/// installed automatically.
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
    private bool _syncing;

    public UpdatesViewModel(UpdateService updates, ISettingsService settings, IShellService shell,
        IDialogService dialogs, ActivityService activity, CrashLog crashLog, AppLog log)
    {
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
        _downloadPage = result.DownloadPage;
        BannerText = result.Message;
        BannerNotes = result.Notes;
        IsBannerVisible = true;
    }
}
