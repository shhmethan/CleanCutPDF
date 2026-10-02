namespace CleanCutPDF.Core.Infrastructure;

/// <summary>
/// Locations of user data. The new application deliberately uses its own
/// folder so it can never modify the working Python app's ~/.cleancutpdf data.
/// </summary>
public sealed class AppPaths
{
    public AppPaths(string? dataDirectory = null, string? legacyDataDirectory = null)
    {
        var home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        DataDirectory = dataDirectory ?? Path.Combine(home, ".cleancutpdf-next");
        LegacyDataDirectory = legacyDataDirectory ?? Path.Combine(home, ".cleancutpdf");
    }

    public string DataDirectory { get; }

    /// <summary>The Python application's data folder. Read-only for this app.</summary>
    public string LegacyDataDirectory { get; }

    public string SettingsFile => Path.Combine(DataDirectory, "settings.json");
    public string CrashLogFile => Path.Combine(DataDirectory, "crash.log");
    public string LicenseFile => Path.Combine(DataDirectory, "license.json");
    public string UpdateCacheFile => Path.Combine(DataDirectory, "update-cache.json");

    /// <summary>The 1.x license file. Read once to carry an existing activation forward; never written.</summary>
    public string LegacyLicenseFile => Path.Combine(LegacyDataDirectory, "license.json");

    public void EnsureCreated() => Directory.CreateDirectory(DataDirectory);
}
