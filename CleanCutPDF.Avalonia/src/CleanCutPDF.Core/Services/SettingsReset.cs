using System.Security.Cryptography;
using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Models;
using CleanCutPDF.Core.Workspaces;

namespace CleanCutPDF.Core.Services;

/// <summary>
/// Reset Settings (1.x Tools › Reset Settings): settings, workspaces, and
/// custom fields go back to the defaults. The license, history, open PDFs,
/// diagnostic logs, and keyboard shortcuts are kept, and the old files are
/// copied to a backup folder first.
/// </summary>
public sealed class SettingsReset(AppPaths paths, ISettingsService settings, WorkspaceStore workspaces, AppLog? log = null)
{
    /// <summary>Letters and digits that cannot be mistaken for each other (no 0/O/1/I), as in 1.x.</summary>
    public const string CodeAlphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";

    public const int CodeLength = 6;

    public static string NewCode() => RandomNumberGenerator.GetString(CodeAlphabet, CodeLength);

    public static bool CodeMatches(string code, string? entered) =>
        string.Equals(code, entered?.Trim(), StringComparison.OrdinalIgnoreCase);

    /// <summary>The defaults, keeping what a reset must not lose.</summary>
    public static AppSettings Defaults(AppSettings current) => new()
    {
        Keybinds = new Dictionary<string, string>(current.Keybinds),
        LegacyImportedUtc = current.LegacyImportedUtc,
        LegacyImportOffered = current.LegacyImportOffered,
        TutorialSeen = current.TutorialSeen,
        LastUpdateCheckUtc = current.LastUpdateCheckUtc
    };

    /// <summary>Backs up, then resets. Returns the backup folder.</summary>
    public async Task<string> ResetAsync(CancellationToken cancellationToken = default)
    {
        await settings.FlushAsync(); // The backup holds what the user last saw.
        var backup = Path.Combine(paths.DataDirectory, "backups", $"reset-{DateTime.Now:yyyyMMdd-HHmmss}");
        Directory.CreateDirectory(backup);
        foreach (var file in new[] { paths.SettingsFile, paths.WorkspacesFile }.Where(File.Exists))
        {
            File.Copy(file, Path.Combine(backup, Path.GetFileName(file)), overwrite: true);
        }

        cancellationToken.ThrowIfCancellationRequested();
        await workspaces.ResetToDefaultsAsync(cancellationToken);
        settings.Replace(Defaults(settings.Current));
        await settings.FlushAsync();
        log?.Info("Settings", "Settings, workspaces, and custom fields were reset to defaults (backup saved)");
        return backup;
    }
}
