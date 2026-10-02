using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Licensing;

namespace CleanCutPDF.Core.Tests;

public sealed class LicenseServiceTests : IDisposable
{
    private const string GoodKey = "TEST-KEY-1234";
    private const string ExpiredKey = "OLD-KEY-9999";

    private readonly TempDirectory _temp = new();
    private readonly FakeHttpHandler _http = new();
    private readonly FakeClock _clock = new(new DateTimeOffset(2026, 10, 2, 12, 0, 0, TimeSpan.Zero));
    private readonly AppPaths _paths;

    public LicenseServiceTests()
    {
        _paths = new AppPaths(Path.Combine(_temp.Path, "next"), Path.Combine(_temp.Path, "legacy"));
        PublishList(includeGoodKey: true);
    }

    [Fact]
    public void Hash_matches_python_sha256_hexdigest()
    {
        // hashlib.sha256(b"abc").hexdigest()
        Assert.Equal("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", LicenseService.HashKey("abc"));
        Assert.Equal(LicenseService.HashKey("abc"), LicenseService.HashKey("  abc \n")); // Python strip()
    }

    [Fact]
    public async Task Activation_stores_only_the_hash()
    {
        var service = NewService();
        await service.LoadAsync();
        Assert.Equal(LicenseStatus.Missing, service.Current.Status);

        var result = await service.ActivateAsync(GoodKey);

        Assert.Equal(LicenseCheckOutcome.Verified, result.Outcome);
        Assert.True(result.State.AllowsUse);
        Assert.Equal("Test Company", result.State.Company);
        var saved = await File.ReadAllTextAsync(_paths.LicenseFile);
        Assert.DoesNotContain(GoodKey, saved);
        Assert.Contains(LicenseService.HashKey(GoodKey), saved);
    }

    [Fact]
    public async Task Wrong_and_expired_keys_are_rejected()
    {
        var service = NewService();
        await service.LoadAsync();

        Assert.Equal(LicenseCheckOutcome.InvalidKey, (await service.ActivateAsync("nope")).Outcome);
        Assert.Equal(LicenseCheckOutcome.Expired, (await service.ActivateAsync(ExpiredKey)).Outcome);
        Assert.False(service.Current.AllowsUse);
    }

    [Fact]
    public async Task Startup_never_goes_online_and_recheck_is_due_weekly()
    {
        await ActivateAsync();
        var requestsAfterActivation = _http.RequestCount;

        _clock.Advance(TimeSpan.FromDays(6));
        var service = NewService();
        var state = await service.LoadAsync();
        Assert.True(state.AllowsUse);
        Assert.False(state.OnlineCheckDue);

        _clock.Advance(TimeSpan.FromDays(1));
        state = await NewService().LoadAsync();
        Assert.True(state.AllowsUse);
        Assert.True(state.OnlineCheckDue);

        Assert.Equal(requestsAfterActivation, _http.RequestCount);
    }

    [Fact]
    public async Task Offline_recheck_keeps_working_until_grace_period_ends()
    {
        await ActivateAsync();
        _http.Offline = true;

        _clock.Advance(TimeSpan.FromDays(20));
        var service = NewService();
        await service.LoadAsync();
        var result = await service.VerifyOnlineAsync();
        Assert.Equal(LicenseCheckOutcome.NetworkError, result.Outcome);
        Assert.True(result.State.AllowsUse);

        _clock.Advance(TimeSpan.FromDays(11)); // 31 days since the last successful check
        var state = await NewService().LoadAsync();
        Assert.Equal(LicenseStatus.VerificationOverdue, state.Status);

        _http.Offline = false;
        service = NewService();
        await service.LoadAsync();
        Assert.Equal(LicenseCheckOutcome.Verified, (await service.VerifyOnlineAsync()).Outcome);
        Assert.True(service.Current.AllowsUse);
    }

    [Fact]
    public async Task Revoked_license_stays_revoked_after_restart()
    {
        await ActivateAsync();
        PublishList(includeGoodKey: false);
        _clock.Advance(TimeSpan.FromDays(8));

        var service = NewService();
        await service.LoadAsync();
        Assert.Equal(LicenseCheckOutcome.Revoked, (await service.VerifyOnlineAsync()).Outcome);

        var state = await NewService().LoadAsync();
        Assert.Equal(LicenseStatus.Revoked, state.Status);
    }

    [Fact]
    public async Task Expiry_date_is_enforced_offline()
    {
        PublishList(includeGoodKey: true, goodKeyExpires: "2026-10-10");
        await ActivateAsync();

        _clock.Advance(TimeSpan.FromDays(9)); // 2026-10-11
        var state = await NewService().LoadAsync();

        Assert.Equal(LicenseStatus.Expired, state.Status);
    }

    [Fact]
    public async Task Legacy_activation_is_carried_over_without_changing_the_legacy_file()
    {
        Directory.CreateDirectory(_paths.LegacyDataDirectory);
        var legacyJson = $"{{\"license_key\": \"{GoodKey}\", \"company\": \"Test Company\"}}";
        await File.WriteAllTextAsync(_paths.LegacyLicenseFile, legacyJson);
        File.SetLastWriteTimeUtc(_paths.LegacyLicenseFile, _clock.Now.AddDays(-2).UtcDateTime);

        var state = await NewService().LoadAsync();

        Assert.True(state.AllowsUse);
        Assert.Equal("Test Company", state.Company);
        Assert.False(state.OnlineCheckDue);
        Assert.Equal(0, _http.RequestCount);
        Assert.Equal(legacyJson, await File.ReadAllTextAsync(_paths.LegacyLicenseFile));
        Assert.DoesNotContain(GoodKey, await File.ReadAllTextAsync(_paths.LicenseFile));
    }

    [Fact]
    public async Task Removed_license_is_not_reimported_from_legacy()
    {
        Directory.CreateDirectory(_paths.LegacyDataDirectory);
        await File.WriteAllTextAsync(_paths.LegacyLicenseFile, $"{{\"license_key\": \"{GoodKey}\", \"company\": \"X\"}}");
        var service = NewService();
        await service.LoadAsync();

        await service.RemoveAsync();

        Assert.Equal(LicenseStatus.Missing, (await NewService().LoadAsync()).Status);
        Assert.True(File.Exists(_paths.LegacyLicenseFile));
    }

    private async Task ActivateAsync()
    {
        var service = NewService();
        await service.LoadAsync();
        Assert.Equal(LicenseCheckOutcome.Verified, (await service.ActivateAsync(GoodKey)).Outcome);
    }

    private LicenseService NewService() =>
        new(new HttpClient(_http, disposeHandler: false), _paths, new CrashLog(_paths), _clock);

    private void PublishList(bool includeGoodKey, string goodKeyExpires = "2099-01-01")
    {
        var good = includeGoodKey
            ? $"\"{LicenseService.HashKey(GoodKey)}\": {{\"company\": \"Test Company\", \"expires\": \"{goodKeyExpires}\"}},"
            : "";
        _http.Respond(RemoteEndpoints.LicenseList,
            $"{{\"licenses\": {{ {good} \"{LicenseService.HashKey(ExpiredKey)}\": {{\"company\": \"Old Co\", \"expires\": \"2020-01-01\"}} }} }}");
    }

    public void Dispose() => _temp.Dispose();
}
