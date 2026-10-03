namespace CleanCutPDF.Core.Models;

public enum AppThemeMode
{
    System,
    Light,
    Dark
}

/// <summary>The color palette layered on top of light/dark (1.x Blue, Green, and Pink themes).</summary>
public enum AppAccent
{
    Blue,
    Green,
    Pink
}

/// <summary>
/// Persisted application settings. Workspaces and custom fields live in
/// workspaces.json; everything else the user can change is here.
/// </summary>
public sealed class AppSettings
{
    public const int DefaultFontSize = 14;
    public const int MinFontSize = 11;
    public const int MaxFontSize = 24;

    public int SchemaVersion { get; set; } = 1;
    public AppThemeMode Theme { get; set; } = AppThemeMode.Light;
    public AppAccent Accent { get; set; } = AppAccent.Blue;

    /// <summary>Font family name; empty means the built-in default (Inter).</summary>
    public string FontFamily { get; set; } = string.Empty;

    public int FontSize { get; set; } = DefaultFontSize;

    /// <summary>Keyboard shortcuts the user changed (action id → gesture); defaults are not stored.</summary>
    public Dictionary<string, string> Keybinds { get; set; } = [];

    public string ExportFolder { get; set; } = string.Empty;
    public string DefaultWorkspace { get; set; } = "Accounting";
    public bool RemoveBlankPages { get; set; } = true;
    public bool MakeClientFolder { get; set; } = true;
    public bool WarnOnFutureDates { get; set; } = true;
    public bool WarnWhenNoSplitMarkers { get; set; } = true;
    public bool AutoRestoreSession { get; set; } = true;
    public bool CheckUpdatesOnStartup { get; set; } = true;
    public DateTimeOffset? LastUpdateCheckUtc { get; set; }

    /// <summary>Also write Debug-level detail to the diagnostic log file.</summary>
    public bool VerboseLogging { get; set; }

    public string QuickSplitFilenameOrder { get; set; } = "Original Name - Part Number";

    public List<FolderShortcut> FolderShortcuts { get; set; } = [];

    /// <summary>When CleanCutPDF 1.x data was last imported (null = never).</summary>
    public DateTimeOffset? LegacyImportedUtc { get; set; }

    public AppSettings Clone()
    {
        var copy = (AppSettings)MemberwiseClone();
        copy.FolderShortcuts = FolderShortcuts.Select(s => s with { }).ToList();
        copy.Keybinds = new Dictionary<string, string>(Keybinds);
        return copy;
    }

    public static int ClampFontSize(int size) => Math.Clamp(size, MinFontSize, MaxFontSize);
}

/// <summary>A frequently used folder shown as a button in the editor (1.x folder shortcuts).</summary>
public sealed record FolderShortcut
{
    public string Label { get; set; } = "";
    public string Path { get; set; } = "";
    public string Icon { get; set; } = "📁";

    /// <summary>Optional #RRGGBB button color.</summary>
    public string Color { get; set; } = "";
}
