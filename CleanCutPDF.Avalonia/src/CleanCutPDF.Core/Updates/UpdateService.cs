using System.Text.Json;
using System.Text.Json.Serialization;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Services;

namespace CleanCutPDF.Core.Updates;

/// <summary>Same format as the 1.x version.json.</summary>
public sealed class UpdateManifest
{
    public string Version { get; set; } = "";

    [JsonPropertyName("download_url")]
    public string? DownloadUrl { get; set; }

    public string? Sha256 { get; set; }

    /// <summary>
    /// True once CleanCutPDF 1.x should offer this version as its upgrade (read
    /// by the 1.x app, not by this one). Leave it off while 2.x is a preview.
    /// </summary>
    [JsonPropertyName("legacy_upgrade")]
    public bool LegacyUpgrade { get; set; }

    public Dictionary<string, List<string>> Changelog { get; set; } = new();
}

public enum UpdateCheckOutcome
{
    UpToDate,
    UpdateAvailable,
    Unavailable
}

public sealed record ReleaseNotes(string Version, IReadOnlyList<string> Lines);

public sealed record UpdateCheckResult(
    UpdateCheckOutcome Outcome,
    string? LatestVersion,
    IReadOnlyList<string> Notes,
    Uri DownloadPage,
    string Message,
    UpdatePackage? Package = null);

/// <summary>
/// Checks the release manifest in the background on every launch (when
/// enabled) and on request. The window never waits for it. The last manifest
/// is cached so release notes and a known update show even when offline.
/// </summary>
public sealed class UpdateService(HttpClient http, ISettingsService settings, AppPaths paths, CrashLog crashLog,
    TimeProvider? clock = null)
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower
    };

    private readonly TimeProvider _clock = clock ?? TimeProvider.System;

    public AppVersion CurrentVersion { get; } = AppVersion.Parse(AppInfo.Version);

    public UpdateManifest? CachedManifest { get; private set; }

    public DateTimeOffset? LastCheckedUtc => settings.Current.LastUpdateCheckUtc;

    /// <summary>True when "check for updates on launch" is enabled.</summary>
    public bool IsAutomaticCheckDue => settings.Current.CheckUpdatesOnStartup;

    public async Task LoadCacheAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            if (File.Exists(paths.UpdateCacheFile))
            {
                await using var stream = File.OpenRead(paths.UpdateCacheFile);
                CachedManifest = await JsonSerializer.DeserializeAsync<UpdateManifest>(stream, JsonOptions, cancellationToken);
            }
        }
        catch (JsonException error)
        {
            crashLog.Write("update-cache.json was unreadable", error);
        }
    }

    /// <summary>The cached result, for showing an available update without going online again.</summary>
    public UpdateCheckResult? CachedResult() => CachedManifest is { } manifest ? Evaluate(manifest) : null;

    public async Task<UpdateCheckResult> CheckAsync(CancellationToken cancellationToken = default)
    {
        UpdateManifest? manifest;
        try
        {
            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            timeout.CancelAfter(RemoteEndpoints.RequestTimeout);
            await using var stream = await http.GetStreamAsync(RemoteEndpoints.UpdateManifest, timeout.Token);
            manifest = await JsonSerializer.DeserializeAsync<UpdateManifest>(stream, JsonOptions, timeout.Token);
        }
        catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            manifest = null; // Timed out.
        }
        catch (Exception error) when (error is HttpRequestException or IOException)
        {
            // Being offline or unable to reach the server is normal, not a crash.
            manifest = null;
        }
        catch (JsonException error)
        {
            crashLog.Write("Update manifest could not be fetched (invalid JSON)", error);
            manifest = null;
        }

        if (manifest is null || string.IsNullOrWhiteSpace(manifest.Version))
        {
            return new UpdateCheckResult(UpdateCheckOutcome.Unavailable, null, [], RemoteEndpoints.ReleasesPage,
                "Update information is not available right now. CleanCutPDF will try again later.");
        }

        CachedManifest = manifest;
        settings.Update(s => s.LastUpdateCheckUtc = _clock.GetUtcNow());
        try
        {
            await AtomicFile.WriteAllTextAsync(paths.UpdateCacheFile, JsonSerializer.Serialize(manifest, JsonOptions),
                cancellationToken);
        }
        catch (IOException error)
        {
            crashLog.Write("Could not cache the update manifest", error);
        }

        return Evaluate(manifest);
    }

    /// <summary>All release notes from the cached manifest, newest first.</summary>
    public IReadOnlyList<ReleaseNotes> AllReleaseNotes() =>
        CachedManifest?.Changelog
            .Select(pair => new ReleaseNotes(pair.Key, pair.Value))
            .OrderByDescending(notes => AppVersion.Parse(notes.Version))
            .ToList()
        ?? [];

    private UpdateCheckResult Evaluate(UpdateManifest manifest)
    {
        var latest = AppVersion.Parse(manifest.Version);
        var notes = manifest.Changelog.TryGetValue(manifest.Version, out var lines) ? lines : [];
        var package = UpdateInstaller.PackageFrom(manifest);

        // The link the Download button opens in a browser. A Windows installer is
        // not a useful link on other systems, so those go to the releases page.
        var page = Uri.TryCreate(manifest.DownloadUrl, UriKind.Absolute, out var url) && url.Scheme == Uri.UriSchemeHttps
                   && (package is null || OperatingSystem.IsWindows())
            ? url
            : RemoteEndpoints.ReleasesPage;

        return latest > CurrentVersion
            ? new UpdateCheckResult(UpdateCheckOutcome.UpdateAvailable, manifest.Version, notes, page,
                $"CleanCutPDF {manifest.Version} is available (you have {CurrentVersion}).", package)
            : new UpdateCheckResult(UpdateCheckOutcome.UpToDate, manifest.Version, notes, page,
                $"CleanCutPDF {CurrentVersion} is up to date.");
    }
}
