namespace CleanCutPDF.Core.Infrastructure;

/// <summary>Appends unexpected errors to crash.log so failures can be diagnosed later.</summary>
public sealed class CrashLog(AppPaths paths)
{
    private readonly object _gate = new();

    public string FilePath => paths.CrashLogFile;

    public void Write(string context, Exception? error)
    {
        try
        {
            lock (_gate)
            {
                paths.EnsureCreated();
                File.AppendAllText(
                    paths.CrashLogFile,
                    $"{Environment.NewLine}[{DateTime.Now:O}] {context}{Environment.NewLine}{error}{Environment.NewLine}");
            }
        }
        catch
        {
            // Crash logging must never throw.
        }
    }
}
