using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.Infrastructure;

namespace CleanCutPDF.Core.Tests;

public sealed class AppLogTests : IDisposable
{
    private readonly TempDirectory _temp = new();

    [Fact]
    public async Task Entries_reach_the_daily_file_and_debug_stays_in_memory_unless_verbose()
    {
        var paths = new AppPaths(_temp.Path);
        await using var log = new AppLog(paths);

        log.Info("Test", "visible info");
        log.Debug("Test", "hidden detail");
        log.Error("Test", "something failed", new InvalidOperationException("boom"));
        await log.FlushAsync(TimeSpan.FromSeconds(5));

        var text = await File.ReadAllTextAsync(log.CurrentFilePath);
        Assert.Contains("INFO    [Test] visible info", text);
        Assert.Contains("ERROR   [Test] something failed", text);
        Assert.Contains("InvalidOperationException: boom", text);
        Assert.DoesNotContain("hidden detail", text);
        Assert.Contains(log.Recent(), e => e.Message == "hidden detail");

        log.Verbose = true;
        log.Debug("Test", "now written");
        await log.FlushAsync(TimeSpan.FromSeconds(5));
        Assert.Contains("now written", await File.ReadAllTextAsync(log.CurrentFilePath));
    }

    [Fact]
    public async Task Crash_report_includes_recent_activity()
    {
        var paths = new AppPaths(_temp.Path);
        await using var log = new AppLog(paths);
        var crashLog = new CrashLog(paths, log);

        log.Info("Inbox", "Opened sample.pdf");
        crashLog.Write("Export failed", new IOException("disk full"));

        var report = await File.ReadAllTextAsync(paths.CrashLogFile);
        Assert.Contains("Export failed", report);
        Assert.Contains("disk full", report);
        Assert.Contains("Opened sample.pdf", report);
    }

    [Fact]
    public async Task Old_log_files_are_deleted_on_startup()
    {
        var paths = new AppPaths(_temp.Path);
        Directory.CreateDirectory(paths.LogsDirectory);
        var old = Path.Combine(paths.LogsDirectory, "cleancutpdf-2020-01-01.log");
        await File.WriteAllTextAsync(old, "old");
        File.SetLastWriteTime(old, DateTime.Now.AddDays(-30));

        await using (var log = new AppLog(paths))
        {
            log.Info("Test", "start");
            await log.FlushAsync(TimeSpan.FromSeconds(5));
        }

        Assert.False(File.Exists(old));
    }

    public void Dispose() => _temp.Dispose();
}
