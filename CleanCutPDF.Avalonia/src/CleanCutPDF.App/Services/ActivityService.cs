using Avalonia.Threading;
using CommunityToolkit.Mvvm.ComponentModel;

namespace CleanCutPDF.App.Services;

/// <summary>
/// Tracks background work for the status bar so the user can see that the app
/// is busy without the window ever freezing.
/// </summary>
public sealed partial class ActivityService : ObservableObject
{
    private readonly List<string> _running = [];
    private CancellationTokenSource? _messageTimeout;

    [ObservableProperty]
    public partial bool IsBusy { get; set; }

    [ObservableProperty]
    public partial string StatusText { get; set; } = "Ready";

    /// <summary>Marks an operation as running until the returned handle is disposed.</summary>
    public IDisposable Begin(string description)
    {
        OnUi(() =>
        {
            _running.Add(description);
            Refresh();
        });
        return new Operation(this, description);
    }

    /// <summary>Shows a short message in the status bar for a few seconds.</summary>
    public void Report(string message)
    {
        OnUi(() =>
        {
            _messageTimeout?.Cancel();
            var timeout = _messageTimeout = new CancellationTokenSource();
            StatusText = message;
            _ = ClearLaterAsync(timeout.Token);
        });
    }

    private async Task ClearLaterAsync(CancellationToken token)
    {
        try
        {
            await Task.Delay(TimeSpan.FromSeconds(6), token);
            Refresh();
        }
        catch (OperationCanceledException)
        {
        }
    }

    private void End(string description)
    {
        OnUi(() =>
        {
            _running.Remove(description);
            Refresh();
        });
    }

    private void Refresh()
    {
        IsBusy = _running.Count > 0;
        StatusText = _running.Count switch
        {
            0 => "Ready",
            1 => _running[0] + "…",
            _ => $"{_running[^1]}… (+{_running.Count - 1} more)"
        };
    }

    private static void OnUi(Action action)
    {
        if (Dispatcher.UIThread.CheckAccess())
        {
            action();
        }
        else
        {
            Dispatcher.UIThread.Post(action);
        }
    }

    private sealed class Operation(ActivityService owner, string description) : IDisposable
    {
        private int _disposed;

        public void Dispose()
        {
            if (Interlocked.Exchange(ref _disposed, 1) == 0)
            {
                owner.End(description);
            }
        }
    }
}
