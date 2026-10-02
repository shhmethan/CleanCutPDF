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
    public bool AutoRestoreSession { get; set; } = true;
    public bool CheckUpdatesOnStartup { get; set; } = true;
    public DateTimeOffset? LastUpdateCheckUtc { get; set; }

    public AppSettings Clone() => (AppSettings)MemberwiseClone();
}
