using CleanCutPDF.Core.Pdf;

namespace CleanCutPDF.Core.Tests;

public sealed class PdfWorkerThreadTests
{
    [Fact]
    public async Task Work_runs_on_the_dedicated_thread()
    {
        using var worker = new PdfWorkerThread();

        var threadId = await worker.InvokeAsync(() => Environment.CurrentManagedThreadId);

        Assert.Equal(worker.ManagedThreadId, threadId);
    }

    [Fact]
    public async Task High_priority_work_jumps_ahead_of_low_priority_backlog()
    {
        using var worker = new PdfWorkerThread();
        using var gate = new ManualResetEventSlim(false);
        var order = new List<string>();

        var blocker = worker.InvokeAsync(() => gate.Wait());
        var low = worker.InvokeAsync(() => { lock (order) order.Add("low"); }, PdfWorkPriority.Low);
        var high = worker.InvokeAsync(() => { lock (order) order.Add("high"); });
        gate.Set();
        await Task.WhenAll(blocker, low, high);

        Assert.Equal(["high", "low"], order);
    }

    [Fact]
    public async Task Exceptions_surface_to_the_caller()
    {
        using var worker = new PdfWorkerThread();

        await Assert.ThrowsAsync<InvalidOperationException>(
            () => worker.InvokeAsync<int>(() => throw new InvalidOperationException("boom")));
    }

    [Fact]
    public async Task Disposing_cancels_queued_work()
    {
        var worker = new PdfWorkerThread();
        using var gate = new ManualResetEventSlim(false);
        using var running = new ManualResetEventSlim(false);
        var blocker = worker.InvokeAsync(() =>
        {
            running.Set();
            gate.Wait(TimeSpan.FromSeconds(2));
        });
        var queued = worker.InvokeAsync(() => 42);
        Assert.True(running.Wait(TimeSpan.FromSeconds(5)));

        var disposeTask = Task.Run(worker.Dispose);
        Assert.True(SpinWait.SpinUntil(() => worker.IsDisposed, TimeSpan.FromSeconds(5)));
        gate.Set();
        await disposeTask;

        await blocker;
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => queued);
    }
}
