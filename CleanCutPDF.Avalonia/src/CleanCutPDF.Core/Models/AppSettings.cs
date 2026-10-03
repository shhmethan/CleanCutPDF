namespace CleanCutPDF.Core.Models;

public enum AppThemeMode
{
    System,
    Light,
    Dark
}

/// <summary>
/// Persisted application settings. Phase 1 holds only the values the shell
/// needs; workspaces, custom fields, and keybinds are added in later phases.
/// </summary>
public sealed class AppSettings
{
    public int SchemaVersion { get; set; } = 1;
    public AppThemeMode Theme { get; set; } = AppThemeMode.Light;
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
        return copy;
    }
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
