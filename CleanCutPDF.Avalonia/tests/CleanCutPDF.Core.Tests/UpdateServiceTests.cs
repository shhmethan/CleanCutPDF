using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Services;
using CleanCutPDF.Core.Updates;

namespace CleanCutPDF.Core.Tests;

public sealed class UpdateServiceTests : IDisposable
{
    private readonly TempDirectory _temp = new();
    private readonly FakeHttpHandler _http = new();
    private readonly FakeClock _clock = new(new DateTimeOffset(2026, 10, 2, 12, 0, 0, TimeSpan.Zero));
    private readonly AppPaths _paths;
    private readonly JsonSettingsService _settings;

    public UpdateServiceTests()
    {
        _paths = new AppPaths(_temp.Path, Path.Combine(_temp.Path, "legacy"));
        _settings = new JsonSettingsService(_paths, new CrashLog(_paths));
    }

    [Theory]
    [InlineData("2.0.0", "2.0.0-alpha.1", 1)]
    [InlineData("2.0.0-alpha.2", "2.0.0-alpha.10", -1)]
    [InlineData("2.0.0-beta", "2.0.0-alpha.5", 1)]
    [InlineData("v1.10.1", "1.9.20", 1)]
    [InlineData("1.10", "1.10.0", 0)]
    [InlineData("2.0.0-alpha.1+build5", "2.0.0-alpha.1", 0)]
    public void Versions_compare_like_semver(string a, string b, int expectedSign) =>
        Assert.Equal(expectedSign, Math.Sign(AppVersion.Parse(a).CompareTo(AppVersion.Parse(b))));

    [Fact]
    public async Task Newer_manifest_reports_update_with_notes()
    {
        await _settings.LoadAsync();
        _http.Respond(RemoteEndpoints.UpdateManifest,
            """{"version": "9.0.0", "download_url": "https://example.com/get", "changelog": {"9.0.0": ["Faster"]}}""");
        var service = NewService();

        var result = await service.CheckAsync();

        Assert.Equal(UpdateCheckOutcome.UpdateAvailable, result.Outcome);
        Assert.Equal(["Faster"], result.Notes);
        Assert.Equal(new Uri("https://example.com/get"), result.DownloadPage);
        Assert.Equal(_clock.Now, service.LastCheckedUtc);
        Assert.True(File.Exists(_paths.UpdateCacheFile));
    }

    [Fact]
    public async Task Older_manifest_is_up_to_date()
    {
        await _settings.LoadAsync();
        _http.Respond(RemoteEndpoints.UpdateManifest, """{"version": "1.10.1", "changelog": {}}""");

        Assert.Equal(UpdateCheckOutcome.UpToDate, (await NewService().CheckAsync()).Outcome);
    }

    [Fact]
    public async Task Failed_check_is_retried_rather_than_waiting_a_week()
    {
        await _settings.LoadAsync();
        _http.Offline = true;
        var service = NewService();

        Assert.Equal(UpdateCheckOutcome.Unavailable, (await service.CheckAsync()).Outcome);
        Assert.Null(service.LastCheckedUtc);
        Assert.True(service.IsAutomaticCheckDue);
    }

    [Fact]
    public async Task Automatic_check_runs_every_launch_unless_turned_off()
    {
        await _settings.LoadAsync();
        _http.Respond(RemoteEndpoints.UpdateManifest, """{"version": "1.0.0"}""");
        var service = NewService();
        await service.CheckAsync();

        _clock.Advance(TimeSpan.FromMinutes(1));
        Assert.True(service.IsAutomaticCheckDue); // even right after a check

        _settings.Update(s => s.CheckUpdatesOnStartup = false);
        Assert.False(service.IsAutomaticCheckDue);
    }

    [Fact]
    public async Task Release_notes_survive_restart_via_cache_newest_first()
    {
        await _settings.LoadAsync();
        _http.Respond(RemoteEndpoints.UpdateManifest,
            """{"version": "2.1.0", "changelog": {"2.0.0": ["Old"], "2.1.0": ["New"]}}""");
        await NewService().CheckAsync();

        var restarted = NewService();
        await restarted.LoadCacheAsync();

        Assert.Equal(["2.1.0", "2.0.0"], restarted.AllReleaseNotes().Select(n => n.Version));
        Assert.Equal(UpdateCheckOutcome.UpdateAvailable, restarted.CachedResult()!.Outcome);
    }

    private UpdateService NewService() =>
        new(new HttpClient(_http, disposeHandler: false), _settings, _paths, new CrashLog(_paths), _clock);

    public void Dispose() => _temp.Dispose();
}
