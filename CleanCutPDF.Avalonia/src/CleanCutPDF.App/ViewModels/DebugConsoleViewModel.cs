using System.Collections.Concurrent;
using System.Collections.ObjectModel;
using Avalonia.Threading;
using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.Services;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace CleanCutPDF.App.ViewModels;

public sealed record LevelOption(LogLevel Level, string Label)
{
    public override string ToString() => Label;
}

/// <summary>
/// Debug console (Ctrl+Alt+D, as in 1.x): every log entry live, including
/// Debug detail that is normally kept out of the log file. New entries are
/// collected off the UI thread and shown in batches, so heavy logging (for
/// example per-page split detection) never slows the window.
/// </summary>
public sealed partial class DebugConsoleViewModel : ObservableObject, IDisposable
{
    private const int MaxShown = 3000;

    private readonly AppLog _log;
    private readonly IShellService _shell;
    private readonly ConcurrentQueue<LogEntry> _incoming = new();
    private readonly List<LogEntry> _all = [];
    private readonly DispatcherTimer _timer;

    public DebugConsoleViewModel(AppLog log, IShellService shell)
    {
        _log = log;
        _shell = shell;
        SelectedLevel = Levels[0];
        foreach (var entry in log.Recent())
        {
            _all.Add(entry);
        }

        Rebuild();
        _log.EntryWritten += OnEntryWritten;
        _timer = new DispatcherTimer(TimeSpan.FromMilliseconds(250), DispatcherPriority.Background, (_, _) => Flush());
        _timer.Start();
    }

    public ObservableCollection<LogEntry> Entries { get; } = [];

    public IReadOnlyList<LevelOption> Levels { get; } =
    [
        new(LogLevel.Debug, "Everything (Debug and up)"),
        new(LogLevel.Info, "Info and up"),
        new(LogLevel.Warning, "Warnings and errors"),
        new(LogLevel.Error, "Errors only")
    ];

    [ObservableProperty]
    public partial LevelOption SelectedLevel { get; set; }

    [ObservableProperty]
    public partial string Search { get; set; } = "";

    [ObservableProperty]
    public partial bool AutoScroll { get; set; } = true;

    [ObservableProperty]
    public partial bool IsPaused { get; set; }

    public string LogsFolder => _log.Directory;

    /// <summary>Raised after new entries are shown, so the view can scroll to the end.</summary>
    public event EventHandler? EntriesAppended;

    partial void OnSelectedLevelChanged(LevelOption value) => Rebuild();
    partial void OnSearchChanged(string value) => Rebuild();

    partial void OnIsPausedChanged(bool value)
    {
        if (!value)
        {
            Flush();
        }
    }

    private void OnEntryWritten(LogEntry entry) => _incoming.Enqueue(entry);

    private void Flush()
    {
        if (IsPaused || _incoming.IsEmpty)
        {
            return;
        }

        var added = false;
        while (_incoming.TryDequeue(out var entry))
        {
            _all.Add(entry);
            if (Matches(entry))
            {
                Entries.Add(entry);
                added = true;
            }
        }

        Trim();
        if (added)
        {
            EntriesAppended?.Invoke(this, EventArgs.Empty);
        }
    }

    private void Rebuild()
    {
        Entries.Clear();
        foreach (var entry in _all.Where(Matches).TakeLast(MaxShown))
        {
            Entries.Add(entry);
        }
    }

    private void Trim()
    {
        if (_all.Count > MaxShown * 2)
        {
            _all.RemoveRange(0, _all.Count - MaxShown);
        }

        while (Entries.Count > MaxShown)
        {
            Entries.RemoveAt(0);
        }
    }

    private bool Matches(LogEntry entry) =>
        entry.Level >= SelectedLevel.Level
        && (Search.Length == 0
            || entry.Message.Contains(Search, StringComparison.OrdinalIgnoreCase)
            || entry.Category.Contains(Search, StringComparison.OrdinalIgnoreCase));

    /// <summary>All shown entries as text (for Copy All).</summary>
    public string AllText() => string.Join(Environment.NewLine, Entries.Select(e => e.Format()));

    [RelayCommand]
    private void ClearView()
    {
        _all.Clear();
        Entries.Clear();
    }

    [RelayCommand]
    private void OpenLogsFolder()
    {
        Directory.CreateDirectory(LogsFolder);
        _shell.OpenFolder(LogsFolder, "Logs folder");
    }

    [RelayCommand]
    private void WriteTestEntry() => _log.Info("Console", "Test entry from the debug console");

    public void Dispose()
    {
        _timer.Stop();
        _log.EntryWritten -= OnEntryWritten;
    }
}
