using CleanCutPDF.App.Services;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Licensing;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace CleanCutPDF.App.ViewModels;

/// <summary>
/// License state for the whole app: drives the lock screen shown over the
/// main window and the License section in Settings.
/// </summary>
public sealed partial class LicenseViewModel(
    LicenseService licenses,
    IDialogService dialogs,
    ActivityService activity,
    AppLifetimeService lifetime,
    CrashLog crashLog) : ObservableObject
{
    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(IsLocked), nameof(Headline), nameof(Explanation), nameof(ShowKeyEntry),
        nameof(ShowRetry), nameof(LicensedTo), nameof(ExpiresText), nameof(LastVerifiedText), nameof(HasLicense))]
    public partial LicenseState State { get; private set; } = licenses.Current;

    /// <summary>False until the saved license has been read, so nothing flashes at startup.</summary>
    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(IsLocked))]
    public partial bool IsLoaded { get; private set; }

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(ActivateCommand), nameof(VerifyNowCommand))]
    public partial bool IsBusy { get; private set; }

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(ActivateCommand))]
    public partial string KeyInput { get; set; } = "";

    [ObservableProperty]
    public partial string? Message { get; private set; }

    public event EventHandler? StateChanged;

    public bool IsLocked => IsLoaded && !State.AllowsUse;
    public bool HasLicense => State.Status != LicenseStatus.Missing;
    public bool ShowKeyEntry => State.Status is LicenseStatus.Missing or LicenseStatus.Expired or LicenseStatus.Revoked;
    public bool ShowRetry => State.Status == LicenseStatus.VerificationOverdue;

    public string? LicensedTo => State.Company;

    public string Headline => State.Status switch
    {
        LicenseStatus.Missing => "Activate CleanCutPDF",
        LicenseStatus.Expired => "Your license has expired",
        LicenseStatus.Revoked => "This license is no longer valid",
        LicenseStatus.VerificationOverdue => "License check needed",
        _ => "Licensed"
    };

    public string Explanation => State.Status switch
    {
        LicenseStatus.Missing => "Enter your CleanCutPDF license key. An internet connection is needed once to activate it.",
        LicenseStatus.Expired => "Enter a renewed license key, or contact your administrator.",
        LicenseStatus.Revoked => "Enter a new license key, or contact your administrator.",
        LicenseStatus.VerificationOverdue =>
            $"CleanCutPDF checks your license online once a week and keeps working offline for up to " +
            $"{LicenseService.OfflineGracePeriod.TotalDays:N0} days. Connect to the internet and try again.",
        _ => ""
    };

    public string ExpiresText => State.Expires is { } date ? date.ToString("MMMM d, yyyy") : "Checked at next verification";

    public string LastVerifiedText => State.LastVerifiedUtc is { } when
        ? when.ToLocalTime().ToString("MMMM d, yyyy h:mm tt")
        : "Never";

    /// <summary>Reads the saved license with no network access, then rechecks in the background if a week has passed.</summary>
    public async Task InitializeAsync()
    {
        try
        {
            State = await licenses.LoadAsync();
        }
        catch (Exception error)
        {
            crashLog.Write("Loading the license failed", error);
            State = licenses.Current;
        }

        IsLoaded = true;
        StateChanged?.Invoke(this, EventArgs.Empty);

        if (State.Status == LicenseStatus.VerificationOverdue)
        {
            await VerifyAsync(showSuccess: false); // The user is waiting on the lock screen.
        }
        else if (State.Status != LicenseStatus.Missing && State.OnlineCheckDue)
        {
            _ = VerifyAsync(showSuccess: false); // Background weekly recheck; the app stays usable.
        }
    }

    [RelayCommand(CanExecute = nameof(CanActivate))]
    private async Task ActivateAsync()
    {
        IsBusy = true;
        Message = "Checking your license…";
        try
        {
            using var _ = activity.Begin("Activating license");
            var result = await licenses.ActivateAsync(KeyInput);
            Message = result.Message;
            if (result.Outcome == LicenseCheckOutcome.Verified)
            {
                KeyInput = "";
                ApplyState(result.State);
                activity.Report(result.Message);
            }
        }
        catch (Exception error)
        {
            crashLog.Write("License activation failed", error);
            Message = "Something went wrong while activating. Details were saved to crash.log.";
        }
        finally
        {
            IsBusy = false;
        }
    }

    private bool CanActivate() => !IsBusy && KeyInput.Trim().Length > 0;

    [RelayCommand(CanExecute = nameof(CanVerify))]
    private Task VerifyNowAsync() => VerifyAsync(showSuccess: true);

    private bool CanVerify() => !IsBusy;

    [RelayCommand]
    private async Task RemoveLicenseAsync()
    {
        var confirmed = await dialogs.ConfirmAsync(
            "Remove License",
            "Remove the license from this copy of CleanCutPDF 2? You will need the key to activate it again.\n\n" +
            "CleanCutPDF 1.x is not affected.",
            "Remove");
        if (!confirmed)
        {
            return;
        }

        await licenses.RemoveAsync();
        Message = null;
        ApplyState(licenses.Current);
    }

    [RelayCommand]
    private void Quit() => lifetime.Quit();

    private async Task VerifyAsync(bool showSuccess)
    {
        IsBusy = true;
        if (IsLocked)
        {
            Message = "Checking your license…";
        }

        try
        {
            using var _ = activity.Begin("Checking license");
            var result = await licenses.VerifyOnlineAsync();
            ApplyState(result.State);

            if (result.Outcome == LicenseCheckOutcome.Verified)
            {
                Message = null;
                if (showSuccess)
                {
                    activity.Report(result.Message);
                }
            }
            else
            {
                Message = result.Message;
                if (result.Outcome == LicenseCheckOutcome.NetworkError && !IsLocked && showSuccess)
                {
                    await dialogs.ShowMessageAsync("License Check", result.Message);
                }
            }
        }
        catch (Exception error)
        {
            crashLog.Write("License verification failed", error);
        }
        finally
        {
            IsBusy = false;
        }
    }

    private void ApplyState(LicenseState state)
    {
        State = state;
        StateChanged?.Invoke(this, EventArgs.Empty);
    }
}
