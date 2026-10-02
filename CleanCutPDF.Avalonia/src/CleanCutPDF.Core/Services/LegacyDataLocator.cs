using CleanCutPDF.Core.Infrastructure;

namespace CleanCutPDF.Core.Services;

public sealed record LegacyDataSummary(
    bool Found,
    string Directory,
    bool HasSettings,
    bool HasSessions,
    bool HasExportLog,
    long ExportLogBytes);

/// <summary>
/// Detects the Python application's ~/.cleancutpdf folder. This class only
/// reads file metadata; it never opens files for writing. A full read-only
/// import of workspaces, fields, and sessions is planned for Phase 3.
/// </summary>
public sealed class LegacyDataLocator(AppPaths paths)
{
    public Task<LegacyDataSummary> InspectAsync(CancellationToken cancellationToken = default) =>
        Task.Run(() =>
        {
            var directory = paths.LegacyDataDirectory;
            if (!System.IO.Directory.Exists(directory))
            {
                return new LegacyDataSummary(false, directory, false, false, false, 0);
            }

            var log = new FileInfo(Path.Combine(directory, "full.log"));
            return new LegacyDataSummary(
                true,
                directory,
                File.Exists(Path.Combine(directory, "settings.json")),
                File.Exists(Path.Combine(directory, "sessions.json")),
                log.Exists,
                log.Exists ? log.Length : 0);
        }, cancellationToken);
}
