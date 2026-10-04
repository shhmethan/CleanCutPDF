using System.Diagnostics;
using System.Security.Cryptography;
using CleanCutPDF.Core.Diagnostics;

namespace CleanCutPDF.Core.Updates;

/// <summary>An installer that can be downloaded and verified.</summary>
public sealed record UpdatePackage(string Version, Uri Url, string Sha256);

public readonly record struct DownloadProgress(long Received, long? Total)
{
    public int? Percent => Total is > 0 ? (int)Math.Min(100, Received * 100 / Total.Value) : null;
}

/// <summary>How this copy of the app was installed (written by the installer next to the program).</summary>
public enum InstallKind
{
    /// <summary>Run from a build folder or copied by hand: the app does not update itself.</summary>
    None,

    /// <summary>Installed normally (shortcuts, Installed apps entry).</summary>
    Registered,

    /// <summary>Installed with /PORTABLE: files only.</summary>
    Portable
}

/// <summary>
/// Installs an update from inside the running app, without a separate updater
/// program (1.x needed CleanCutPDFUpdater.exe). The app downloads the new
/// installer, checks its SHA-256 against the manifest, starts it silently, and
/// closes. The installer waits for the app to exit, replaces the files, and
/// starts the app again.
/// </summary>
public sealed class UpdateInstaller(HttpClient http, AppLog? log = null, string? installDirectory = null,
    string? downloadDirectory = null)
{
    public const string MarkerFile = "install.marker";

    public string InstallDirectory { get; } =
        Path.TrimEndingDirectorySeparator(Path.GetFullPath(installDirectory ?? AppContext.BaseDirectory));

    public string DownloadDirectory { get; } = downloadDirectory ?? Path.Combine(Path.GetTempPath(), "CleanCutPDFUpdate");

    public InstallKind Kind
    {
        get
        {
            try
            {
                var marker = Path.Combine(InstallDirectory, MarkerFile);
                return !File.Exists(marker) ? InstallKind.None
                    : File.ReadAllText(marker).Trim().Equals("portable", StringComparison.OrdinalIgnoreCase) ? InstallKind.Portable
                    : InstallKind.Registered;
            }
            catch (Exception error) when (error is IOException or UnauthorizedAccessException)
            {
                return InstallKind.None;
            }
        }
    }

    /// <summary>
    /// The installer a manifest offers, or null when it has none that can be
    /// trusted: the link must be https (plain http only for this computer,
    /// used when testing), point at an .exe, and come with a SHA-256.
    /// </summary>
    public static UpdatePackage? PackageFrom(UpdateManifest manifest)
    {
        var hash = (manifest.Sha256 ?? "").Trim();
        if (hash.Length != 64 || !hash.All(Uri.IsHexDigit)
            || !Uri.TryCreate(manifest.DownloadUrl, UriKind.Absolute, out var url)
            || !url.AbsolutePath.EndsWith(".exe", StringComparison.OrdinalIgnoreCase))
        {
            return null;
        }

        var secure = url.Scheme == Uri.UriSchemeHttps || (url.Scheme == Uri.UriSchemeHttp && url.IsLoopback);
        return secure ? new UpdatePackage(manifest.Version, url, hash.ToLowerInvariant()) : null;
    }

    /// <summary>True when this copy can install that manifest's update by itself.</summary>
    public bool CanInstall(UpdateManifest? manifest) =>
        manifest is not null && OperatingSystem.IsWindows() && Kind != InstallKind.None && PackageFrom(manifest) is not null;

    /// <summary>
    /// Downloads the installer and verifies it. A file that does not match the
    /// expected SHA-256 is deleted and never run. Returns the installer's path.
    /// </summary>
    public async Task<string> DownloadAsync(UpdatePackage package, IProgress<DownloadProgress>? progress = null,
        CancellationToken cancellationToken = default)
    {
        Directory.CreateDirectory(DownloadDirectory);
        var safeVersion = string.Concat(package.Version.Select(c => char.IsLetterOrDigit(c) || c is '.' or '-' ? c : '_'));
        var target = Path.Combine(DownloadDirectory, $"CleanCutPDF-{safeVersion}-Setup.exe");

        // An earlier attempt may already have fetched it (for example the install was cancelled).
        if (File.Exists(target) && await HashAsync(target, cancellationToken) == package.Sha256)
        {
            log?.Info("Updates", $"Installer for {package.Version} was already downloaded");
            return target;
        }

        var partial = target + ".part";
        try
        {
            using var response = await http.GetAsync(package.Url, HttpCompletionOption.ResponseHeadersRead, cancellationToken);
            response.EnsureSuccessStatusCode();
            var total = response.Content.Headers.ContentLength;
            using var sha = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
            await using (var source = await response.Content.ReadAsStreamAsync(cancellationToken))
            await using (var file = new FileStream(partial, FileMode.Create, FileAccess.Write, FileShare.None, 1 << 16, useAsync: true))
            {
                var buffer = new byte[1 << 16];
                long received = 0;
                int read;
                while ((read = await source.ReadAsync(buffer, cancellationToken)) > 0)
                {
                    await file.WriteAsync(buffer.AsMemory(0, read), cancellationToken);
                    sha.AppendData(buffer, 0, read);
                    received += read;
                    progress?.Report(new DownloadProgress(received, total));
                }
            }

            var actual = Convert.ToHexStringLower(sha.GetHashAndReset());
            if (actual != package.Sha256)
            {
                log?.Error("Updates", $"Installer for {package.Version} failed verification and was discarded");
                throw new InvalidDataException(
                    "The downloaded update did not match its expected signature (SHA-256), so it was not installed.");
            }

            File.Move(partial, target, overwrite: true);
            log?.Info("Updates", $"Downloaded and verified the installer for {package.Version}");
            return target;
        }
        finally
        {
            try
            {
                File.Delete(partial);
            }
            catch (IOException)
            {
                // Left for the next attempt to overwrite.
            }
        }
    }

    /// <summary>
    /// The command that installs over this copy: silent, into the folder the
    /// app is running from, and starting the app again afterwards.
    /// </summary>
    public ProcessStartInfo InstallCommand(string installerPath)
    {
        // NSIS: /D must be last and is not quoted, even when the path has spaces.
        var portable = Kind == InstallKind.Portable ? " /PORTABLE" : "";
        return new ProcessStartInfo(installerPath, $"/S /RELAUNCH{portable} /D={InstallDirectory}")
        {
            UseShellExecute = false,
            WorkingDirectory = Path.GetDirectoryName(installerPath) ?? ""
        };
    }

    /// <summary>Starts the installer. The caller must then close the app so its files can be replaced.</summary>
    public void Launch(string installerPath)
    {
        log?.Info("Updates", "Starting the installer; CleanCutPDF will close and reopen");
        using var process = Process.Start(InstallCommand(installerPath))
                            ?? throw new InvalidOperationException("The installer could not be started.");
    }

    private static async Task<string> HashAsync(string path, CancellationToken cancellationToken)
    {
        await using var stream = File.OpenRead(path);
        return Convert.ToHexStringLower(await SHA256.HashDataAsync(stream, cancellationToken));
    }
}
