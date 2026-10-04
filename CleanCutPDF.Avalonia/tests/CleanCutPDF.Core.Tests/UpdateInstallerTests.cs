using System.Security.Cryptography;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Services;
using CleanCutPDF.Core.Updates;

namespace CleanCutPDF.Core.Tests;

public sealed class UpdateInstallerTests : IDisposable
{
    private static readonly Uri InstallerUrl = new("https://example.com/releases/CleanCutPDF-9.0.0-Setup.exe");
    private static readonly byte[] InstallerBytes = Enumerable.Range(0, 300_000).Select(i => (byte)(i * 31)).ToArray();
    private static readonly string InstallerHash = Convert.ToHexStringLower(SHA256.HashData(InstallerBytes));

    private readonly TempDirectory _temp = new();
    private readonly FakeHttpHandler _http = new();
    private readonly string _installDir;
    private readonly string _downloadDir;

    public UpdateInstallerTests()
    {
        _installDir = Path.Combine(_temp.Path, "Program Files", "CleanCutPDF"); // A space, like real install folders.
        _downloadDir = Path.Combine(_temp.Path, "downloads");
        Directory.CreateDirectory(_installDir);
    }

    private UpdateInstaller Installer() => new(new HttpClient(_http), null, _installDir, _downloadDir);

    private void MarkInstalled(string kind) => File.WriteAllText(Path.Combine(_installDir, UpdateInstaller.MarkerFile), kind);

    private static UpdateManifest Manifest(string? url = null, string? sha = null) => new()
    {
        Version = "9.0.0",
        DownloadUrl = url ?? InstallerUrl.AbsoluteUri,
        Sha256 = sha ?? InstallerHash
    };

    [Fact]
    public void A_package_needs_a_secure_exe_link_and_a_sha256()
    {
        var package = UpdateInstaller.PackageFrom(Manifest(sha: InstallerHash.ToUpperInvariant()))!;
        Assert.Equal(("9.0.0", InstallerUrl, InstallerHash), (package.Version, package.Url, package.Sha256));

        Assert.Null(UpdateInstaller.PackageFrom(Manifest(sha: ""))); // 1.x treated the hash as optional; here it is required.
        Assert.Null(UpdateInstaller.PackageFrom(Manifest(sha: "abc123")));
        Assert.Null(UpdateInstaller.PackageFrom(Manifest(sha: new string('z', 64))));
        Assert.Null(UpdateInstaller.PackageFrom(Manifest(url: "https://github.com/shhmethan/CleanCutPDF/releases"))); // A page, not an installer.
        Assert.Null(UpdateInstaller.PackageFrom(Manifest(url: "http://example.com/Setup.exe"))); // Not encrypted.
        Assert.Null(UpdateInstaller.PackageFrom(Manifest(url: "ftp://example.com/Setup.exe")));
        Assert.Null(UpdateInstaller.PackageFrom(Manifest(url: "not a link")));

        // Plain http is accepted only for this computer (release rehearsals).
        Assert.NotNull(UpdateInstaller.PackageFrom(Manifest(url: "http://127.0.0.1:8765/Setup.exe")));
        Assert.NotNull(UpdateInstaller.PackageFrom(Manifest(url: "http://localhost/Setup.EXE?x=1")));
    }

    [Fact]
    public void Only_an_installed_copy_updates_itself()
    {
        var installer = Installer();
        Assert.Equal(InstallKind.None, installer.Kind); // A build folder: no marker.
        Assert.False(installer.CanInstall(Manifest()));

        MarkInstalled("registered");
        Assert.Equal(InstallKind.Registered, installer.Kind);
        Assert.Equal(OperatingSystem.IsWindows(), installer.CanInstall(Manifest()));
        Assert.False(installer.CanInstall(Manifest(sha: "")));
        Assert.False(installer.CanInstall(null));

        MarkInstalled("portable\r\n");
        Assert.Equal(InstallKind.Portable, installer.Kind);
    }

    [Fact]
    public async Task Download_is_verified_and_reports_progress()
    {
        _http.RespondFile(InstallerUrl, InstallerBytes);
        var reports = new List<DownloadProgress>();
        var progress = new SynchronousProgress(reports.Add);

        var path = await Installer().DownloadAsync(UpdateInstaller.PackageFrom(Manifest())!, progress);

        Assert.Equal(Path.Combine(_downloadDir, "CleanCutPDF-9.0.0-Setup.exe"), path);
        Assert.Equal(InstallerBytes, await File.ReadAllBytesAsync(path));
        Assert.Equal(100, reports[^1].Percent);
        Assert.Equal(InstallerBytes.Length, reports[^1].Received);
        Assert.Empty(Directory.GetFiles(_downloadDir, "*.part"));
    }

    [Fact]
    public async Task A_download_that_does_not_match_its_sha256_is_discarded_and_never_run()
    {
        var tampered = InstallerBytes.ToArray();
        tampered[1000] ^= 0xFF;
        _http.RespondFile(InstallerUrl, tampered);

        var error = await Assert.ThrowsAsync<InvalidDataException>(
            () => Installer().DownloadAsync(UpdateInstaller.PackageFrom(Manifest())!));

        Assert.Contains("SHA-256", error.Message);
        Assert.Empty(Directory.GetFiles(_downloadDir)); // Nothing is left to run by mistake.
    }

    [Fact]
    public async Task A_failed_or_cancelled_download_leaves_nothing_behind()
    {
        await Assert.ThrowsAsync<HttpRequestException>( // 404
            () => Installer().DownloadAsync(UpdateInstaller.PackageFrom(Manifest())!));

        _http.RespondFile(InstallerUrl, InstallerBytes);
        using var cancelled = new CancellationTokenSource();
        cancelled.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(
            () => Installer().DownloadAsync(UpdateInstaller.PackageFrom(Manifest())!, null, cancelled.Token));

        Assert.Empty(Directory.GetFiles(_downloadDir));
    }

    [Fact]
    public async Task An_installer_already_downloaded_is_reused_only_if_it_still_verifies()
    {
        _http.RespondFile(InstallerUrl, InstallerBytes);
        var package = UpdateInstaller.PackageFrom(Manifest())!;
        var path = await Installer().DownloadAsync(package);
        Assert.Equal(1, _http.RequestCount);

        await Installer().DownloadAsync(package);
        Assert.Equal(1, _http.RequestCount); // Not downloaded again.

        await File.WriteAllTextAsync(path, "changed on disk");
        await Installer().DownloadAsync(package);
        Assert.Equal(2, _http.RequestCount); // A changed file is not trusted.
        Assert.Equal(InstallerBytes, await File.ReadAllBytesAsync(path));
    }

    [Fact]
    public void Install_command_is_silent_reopens_the_app_and_targets_this_copy()
    {
        var setup = Path.Combine(_downloadDir, "CleanCutPDF-9.0.0-Setup.exe");

        MarkInstalled("registered");
        var command = Installer().InstallCommand(setup);
        Assert.Equal(setup, command.FileName);
        Assert.Equal($"/S /RELAUNCH /D={_installDir}", command.Arguments); // /D last and unquoted, as NSIS requires.
        Assert.DoesNotContain("\"", command.Arguments);
        Assert.False(command.Arguments.EndsWith('\\'));

        MarkInstalled("portable");
        Assert.Equal($"/S /RELAUNCH /PORTABLE /D={_installDir}", Installer().InstallCommand(setup).Arguments);
    }

    [Fact]
    public async Task Update_check_offers_the_installer_when_the_manifest_has_one()
    {
        var paths = new AppPaths(Path.Combine(_temp.Path, "data"), Path.Combine(_temp.Path, "legacy"));
        var settings = new JsonSettingsService(paths, new CrashLog(paths));
        await settings.LoadAsync();
        var updates = new UpdateService(new HttpClient(_http), settings, paths, new CrashLog(paths));

        _http.Respond(RemoteEndpoints.UpdateManifest,
            $$"""{"version": "9.0.0", "download_url": "{{InstallerUrl}}", "sha256": "{{InstallerHash}}", "legacy_upgrade": true, "changelog": { } }""");
        var result = await updates.CheckAsync();
        Assert.Equal(InstallerUrl, result.Package!.Url);
        Assert.True(updates.CachedManifest!.LegacyUpgrade);

        // A manifest with only a web page (as during the alphas) still works: link, no installer.
        _http.Respond(RemoteEndpoints.UpdateManifest,
            """{"version": "9.0.0", "download_url": "https://github.com/shhmethan/CleanCutPDF/releases", "sha256": "", "changelog": {}}""");
        result = await updates.CheckAsync();
        Assert.Null(result.Package);
        Assert.Equal(UpdateCheckOutcome.UpdateAvailable, result.Outcome);
        Assert.False(updates.CachedManifest!.LegacyUpgrade);
    }

    public void Dispose() => _temp.Dispose();

    /// <summary>Progress&lt;T&gt; posts to a context; tests want the reports immediately.</summary>
    private sealed class SynchronousProgress(Action<DownloadProgress> report) : IProgress<DownloadProgress>
    {
        public void Report(DownloadProgress value) => report(value);
    }
}
