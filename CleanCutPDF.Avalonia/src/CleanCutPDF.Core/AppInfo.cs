using System.Reflection;

namespace CleanCutPDF.Core;

/// <summary>Version and naming information shared by the UI and services.</summary>
public static class AppInfo
{
    public const string ProductName = "CleanCutPDF";

    /// <summary>Last version of the Python application this build was modeled on.</summary>
    public const string ReferenceLegacyVersion = "2.0.0";

    public static string Version { get; } =
        typeof(AppInfo).Assembly
            .GetCustomAttribute<AssemblyInformationalVersionAttribute>()?
            .InformationalVersion.Split('+')[0]
        ?? "0.0.0";
}
