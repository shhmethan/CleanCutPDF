using System.Globalization;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading.Channels;
using CleanCutPDF.Core.Infrastructure;

namespace CleanCutPDF.Core.Diagnostics;

public enum LogLevel
{
    Debug,
    Info,
    Warning,
    Error
}

public sealed record LogEntry(DateTimeOffset Time, LogLevel Level, string Category, string Message, Exception? Error)
{
    /// <summary>The formatted line (for display).</summary>
    public string Text => Format();

    public string Format()
    {
        var builder = new StringBuilder()
            .Append(Time.ToLocalTime().ToString("yyyy-MM-dd HH:mm:ss.fff", CultureInfo.InvariantCulture))
            .Append(' ').Append(Level.ToString().ToUpperInvariant().PadRight(7))
            .Append(" [").Append(Category).Append("] ")
            .Append(Message);
        if (Error is not null)
        {
            builder.AppendLine().Append(Error);
        }

        return builder.ToString();
    }
}

/// <summary>
/// Diagnostic log for troubleshooting (separate from the export history).
///
/// Callers never wait on disk I/O: entries go into a channel and a background
/// task appends them to logs/cleancutpdf-YYYY-MM-DD.log. Debug entries are kept
/// in memory only unless verbose logging is on, so per-page detail during
/// split detection costs nothing on disk. The most recent entries are kept in
/// memory and attached to crash reports.
///
/// Privacy: log file names and actions, never client names, field values, or
/// license keys.
/// </summary>
public sealed class AppLog : IAsyncDisposable, IDisposable
{
    public const int RetainedDays = 14;
    private const int RecentCapacity = 500;
    private const long MaxFileBytes = 10L * 1024 * 1024;

    private readonly string _directory;
    private readonly Channel<LogEntry> _channel = Channel.CreateUnbounded<LogEntry>(
        new UnboundedChannelOptions { SingleReader = true });
    private readonly Queue<LogEntry> _recent = new();
    private readonly object _recentGate = new();
    private readonly Task _writer;
    private readonly TimeProvider _clock;

    public AppLog(AppPaths paths, TimeProvider? clock = null)
    {
        _directory = paths.LogsDirectory;
        _clock = clock ?? TimeProvider.System;
        _writer = Task.Run(WriteLoopAsync);
    }

    /// <summary>Every entry, including Debug, as it is written (any thread).</summary>
    public event Action<LogEntry>? EntryWritten;

    /// <summary>When true, Debug entries are also written to disk.</summary>
    public bool Verbose { get; set; }

    public string Directory => _directory;

    public string CurrentFilePath => Path.Combine(_directory, FileNameFor(_clock.GetLocalNow()));

    public void Debug(string category, string message) => Write(LogLevel.Debug, category, message);
    public void Info(string category, string message) => Write(LogLevel.Info, category, message);
    public void Warning(string category, string message, Exception? error = null) => Write(LogLevel.Warning, category, message, error);
    public void Error(string category, string message, Exception? error = null) => Write(LogLevel.Error, category, message, error);

    public void Write(LogLevel level, string category, string message, Exception? error = null)
    {
        var entry = new LogEntry(_clock.GetUtcNow(), level, category, message, error);
        lock (_recentGate)
        {
            _recent.Enqueue(entry);
            while (_recent.Count > RecentCapacity)
            {
                _recent.Dequeue();
            }
        }

        if (level != LogLevel.Debug || Verbose)
        {
            _channel.Writer.TryWrite(entry);
        }

        // Live feed for the debug console (Ctrl+Alt+D). Raised on the caller's thread.
        EntryWritten?.Invoke(entry);

        System.Diagnostics.Debug.WriteLine(entry.Format());
    }

    /// <summary>The most recent entries (including Debug), oldest first.</summary>
    public IReadOnlyList<LogEntry> Recent(int count = RecentCapacity)
    {
        lock (_recentGate)
        {
            return _recent.Skip(Math.Max(0, _recent.Count - count)).ToList();
        }
    }

    /// <summary>Writes a header describing this run, to make reports self-explanatory.</summary>
    public void WriteSessionHeader(string dataDirectory) =>
        Info("Startup",
            $"{AppInfo.ProductName} {AppInfo.Version} | {RuntimeInformation.OSDescription} " +
            $"({RuntimeInformation.OSArchitecture}) | .NET {Environment.Version} | data: {dataDirectory}");

    /// <summary>Waits until everything queued so far has reached the disk.</summary>
    public async Task FlushAsync(TimeSpan timeout)
    {
        var marker = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        _flushRequests.Enqueue(marker);
        _channel.Writer.TryWrite(FlushMarker);
        await Task.WhenAny(marker.Task, Task.Delay(timeout)).ConfigureAwait(false);
    }

    private static readonly LogEntry FlushMarker = new(default, LogLevel.Debug, "", "", null);
    private readonly System.Collections.Concurrent.ConcurrentQueue<TaskCompletionSource> _flushRequests = new();

    private async Task WriteLoopAsync()
    {
        try
        {
            System.IO.Directory.CreateDirectory(_directory);
            DeleteOldFiles();
        }
        catch
        {
            // Logging must never take the app down.
        }

        var batch = new StringBuilder();
        await foreach (var entry in ReadBatchesAsync())
        {
            if (ReferenceEquals(entry, FlushMarker))
            {
                await AppendAsync(batch);
                while (_flushRequests.TryDequeue(out var request))
                {
                    request.TrySetResult();
                }

                continue;
            }

            batch.AppendLine(entry.Format());
            if (!_channel.Reader.TryPeek(out _))
            {
                await AppendAsync(batch);
            }
        }

        await AppendAsync(batch);
    }

    private IAsyncEnumerable<LogEntry> ReadBatchesAsync() => _channel.Reader.ReadAllAsync();

    private async Task AppendAsync(StringBuilder batch)
    {
        if (batch.Length == 0)
        {
            return;
        }

        try
        {
            var path = CurrentFilePath;
            var info = new FileInfo(path);
            if (info.Exists && info.Length > MaxFileBytes)
            {
                // Keep the app usable even if something logs in a loop.
                File.Move(path, Path.ChangeExtension(path, $".{_clock.GetLocalNow():HHmmss}.log"), overwrite: true);
            }

            await File.AppendAllTextAsync(path, batch.ToString());
        }
        catch
        {
            // Disk full or folder locked: drop this batch rather than crash.
        }

        batch.Clear();
    }

    private void DeleteOldFiles()
    {
        var cutoff = _clock.GetLocalNow().DateTime.AddDays(-RetainedDays);
        foreach (var file in new DirectoryInfo(_directory).EnumerateFiles("cleancutpdf-*.log"))
        {
            if (file.LastWriteTime < cutoff)
            {
                file.Delete();
            }
        }
    }

    private static string FileNameFor(DateTimeOffset localNow) => $"cleancutpdf-{localNow:yyyy-MM-dd}.log";

    public void Dispose() => DisposeAsync().AsTask().Wait(TimeSpan.FromSeconds(3));

    public async ValueTask DisposeAsync()
    {
        _channel.Writer.TryComplete();
        await Task.WhenAny(_writer, Task.Delay(TimeSpan.FromSeconds(3))).ConfigureAwait(false);
    }
}
