using System.Collections.Concurrent;

namespace CleanCutPDF.Core.Pdf;

public enum PdfWorkPriority
{
    /// <summary>Work the user is waiting on right now (visible preview, open).</summary>
    High = 0,

    /// <summary>Speculative work such as prefetching the next page.</summary>
    Low = 1
}

/// <summary>
/// A single dedicated thread that owns every PDFium call. PDFium is not
/// thread-safe, so all native work is serialized here, while callers simply
/// await a Task and the UI thread is never blocked.
///
/// Queued work whose CancellationToken is cancelled before it starts is
/// skipped, so rapidly paging through a document does not build a backlog.
/// </summary>
public sealed class PdfWorkerThread : IDisposable
{
    private readonly BlockingCollection<Action>[] _queues =
    [
        new BlockingCollection<Action>(new ConcurrentQueue<Action>()),
        new BlockingCollection<Action>(new ConcurrentQueue<Action>())
    ];

    private readonly Thread _thread;
    private readonly CancellationTokenSource _shutdown = new();
    private volatile bool _disposed;

    public PdfWorkerThread(Action? onStart = null, Action? onStop = null)
    {
        _thread = new Thread(() => Run(onStart, onStop))
        {
            IsBackground = true,
            Name = "CleanCutPDF PDF worker"
        };
        _thread.Start();
    }

    public int ManagedThreadId => _thread.ManagedThreadId;

    internal bool IsDisposed => _disposed;

    public Task<T> InvokeAsync<T>(Func<T> work, PdfWorkPriority priority = PdfWorkPriority.High,
        CancellationToken cancellationToken = default)
    {
        ObjectDisposedException.ThrowIf(_disposed, this);
        if (cancellationToken.IsCancellationRequested)
        {
            return Task.FromCanceled<T>(cancellationToken);
        }

        var completion = new TaskCompletionSource<T>(TaskCreationOptions.RunContinuationsAsynchronously);
        var registration = cancellationToken.Register(() => completion.TrySetCanceled(cancellationToken));

        _queues[(int)priority].Add(() =>
        {
            try
            {
                if (cancellationToken.IsCancellationRequested)
                {
                    completion.TrySetCanceled(cancellationToken);
                    return;
                }

                if (_disposed)
                {
                    completion.TrySetCanceled();
                    return;
                }

                completion.TrySetResult(work());
            }
            catch (OperationCanceledException error) when (error.CancellationToken == cancellationToken)
            {
                completion.TrySetCanceled(cancellationToken);
            }
            catch (Exception error)
            {
                completion.TrySetException(error);
            }
            finally
            {
                registration.Dispose();
            }
        });

        return completion.Task;
    }

    public Task InvokeAsync(Action work, PdfWorkPriority priority = PdfWorkPriority.High,
        CancellationToken cancellationToken = default) =>
        InvokeAsync(() =>
        {
            work();
            return true;
        }, priority, cancellationToken);

    private void Run(Action? onStart, Action? onStop)
    {
        onStart?.Invoke();
        try
        {
            while (!_shutdown.IsCancellationRequested)
            {
                Action? work;
                try
                {
                    // TakeFromAny checks the queues in array order, so High always wins.
                    BlockingCollection<Action>.TakeFromAny(_queues, out work, _shutdown.Token);
                }
                catch (OperationCanceledException)
                {
                    break;
                }
                catch (ArgumentException)
                {
                    break; // All queues completed.
                }

                work!();
            }
        }
        finally
        {
            // Complete anything still queued (as cancelled) so no caller awaits forever.
            foreach (var queue in _queues)
            {
                while (queue.TryTake(out var pending))
                {
                    pending();
                }
            }

            onStop?.Invoke();
        }
    }

    public void Dispose()
    {
        if (_disposed)
        {
            return;
        }

        _disposed = true;
        foreach (var queue in _queues)
        {
            queue.CompleteAdding();
        }

        _shutdown.Cancel();
        _thread.Join(TimeSpan.FromSeconds(5));
        _shutdown.Dispose();
        foreach (var queue in _queues)
        {
            queue.Dispose();
        }
    }
}
