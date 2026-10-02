using CleanCutPDF.Core.Models;

namespace CleanCutPDF.Core.Pdf;

/// <summary>
/// High-level preview API used by the UI: cache lookup, background render,
/// cancellation of stale requests, and low-priority prefetch of neighbours.
/// </summary>
public sealed class PagePreviewService(IPdfEngine engine, PagePreviewCache cache)
{
    /// <summary>Widths are bucketed so small window resizes reuse cached renders.</summary>
    public static int BucketWidth(double requestedPixels)
    {
        const int bucket = 200;
        var width = (int)Math.Ceiling(Math.Max(bucket, requestedPixels) / bucket) * bucket;
        return Math.Min(width, 2400);
    }

    public async Task<RenderedPage> GetPageAsync(string path, int pageIndex, int width, CancellationToken cancellationToken)
    {
        var info = await engine.OpenAsync(path, cancellationToken);
        var key = new PreviewKey(info.Path, info.Signature, pageIndex, width);
        if (cache.TryGet(key, out var cached))
        {
            return cached;
        }

        var page = await engine.RenderPageAsync(info.Path, pageIndex, width, PdfWorkPriority.High, cancellationToken);
        cache.Add(key, page);
        return page;
    }

    /// <summary>Fire-and-forget render of nearby pages at low priority.</summary>
    public void Prefetch(string path, int pageIndex, int pageCount, int width, CancellationToken cancellationToken)
    {
        foreach (var neighbour in new[] { pageIndex + 1, pageIndex - 1 })
        {
            if (neighbour < 0 || neighbour >= pageCount)
            {
                continue;
            }

            _ = PrefetchOneAsync(path, neighbour, width, cancellationToken);
        }
    }

    public async Task ForgetDocumentAsync(string path)
    {
        var fullPath = Path.GetFullPath(path);
        cache.Invalidate(fullPath);
        await engine.CloseAsync(fullPath);
    }

    private async Task PrefetchOneAsync(string path, int pageIndex, int width, CancellationToken cancellationToken)
    {
        try
        {
            var info = await engine.OpenAsync(path, cancellationToken);
            var key = new PreviewKey(info.Path, info.Signature, pageIndex, width);
            if (cache.TryGet(key, out _))
            {
                return;
            }

            var page = await engine.RenderPageAsync(info.Path, pageIndex, width, PdfWorkPriority.Low, cancellationToken);
            cache.Add(key, page);
        }
        catch
        {
            // Prefetch is best-effort; failures surface when the page is actually requested.
        }
    }
}
