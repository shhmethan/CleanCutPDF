namespace CleanCutPDF.Core.Infrastructure;

/// <summary>Online resources used by the app. All are plain HTTPS GETs with certificate validation on.</summary>
public static class RemoteEndpoints
{
    /// <summary>Same license list the 1.x app uses (SHA-256 key hash → company, expiry).</summary>
    public static readonly Uri LicenseList =
        new("https://raw.githubusercontent.com/shhmethan/CleanCutPDF/refs/heads/master1/licenses.json");

    /// <summary>
    /// Release manifest for the 2.x app. Deliberately separate from the 1.x
    /// version.json, whose download_url points at the Python executable.
    /// </summary>
    public static readonly Uri UpdateManifest = ManifestOverride()
        ?? new("https://raw.githubusercontent.com/shhmethan/CleanCutPDF/refs/heads/master1/CleanCutPDF.Avalonia/version.json");

    /// <summary>
    /// CLEANCUTPDF_UPDATE_MANIFEST points the update check at another manifest,
    /// for rehearsing a release before it is published. Only https, or http on
    /// this computer, is accepted.
    /// </summary>
    private static Uri? ManifestOverride() =>
        Uri.TryCreate(Environment.GetEnvironmentVariable("CLEANCUTPDF_UPDATE_MANIFEST"), UriKind.Absolute, out var url)
        && (url.Scheme == Uri.UriSchemeHttps || (url.Scheme == Uri.UriSchemeHttp && url.IsLoopback))
            ? url
            : null;

    public static readonly Uri ReleasesPage = new("https://github.com/shhmethan/CleanCutPDF/releases");

    public static readonly TimeSpan RequestTimeout = TimeSpan.FromSeconds(10);
}
