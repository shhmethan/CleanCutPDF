using CleanCutPDF.Core.Diagnostics;

namespace CleanCutPDF.Core.Infrastructure;

/// <summary>
/// Records unexpected errors. Each error goes to the diagnostic log and to
/// crash.log, together with the last few log entries so the report shows what
/// the user was doing just before (the role last_action.json played in 1.x).
/// </summary>
public sealed class CrashLog(AppPaths paths, AppLog? log = null)
{
    private const int ContextEntries = 40;
    private readonly object _gate = new();

    public string FilePath => paths.CrashLogFile;

    public void Write(string context, Exception? error)
    {
        try
        {
            log?.Error("Error", context, error);
            lock (_gate)
            {
                paths.EnsureCreated();
                using var writer = File.AppendText(paths.CrashLogFile);
                writer.WriteLine();
                writer.WriteLine($"[{DateTime.Now:O}] {AppInfo.ProductName} {AppInfo.Version}: {context}");
                writer.WriteLine(error);
                if (log is not null)
                {
                    writer.WriteLine("  Recent activity:");
                    foreach (var entry in log.Recent(ContextEntries).Where(e => e.Error is null))
                    {
                        writer.WriteLine("    " + entry.Format());
                    }
                }
            }
        }
        catch
        {
            // Crash logging must never throw.
        }
    }
}
