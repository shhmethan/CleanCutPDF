using CleanCutPDF.Core.Models;
using CleanCutPDF.Core.Pdf;

namespace CleanCutPDF.Core.Tests;

public sealed class PagePreviewTests : IDisposable
{
    private readonly TempDirectory _temp = new();
    private readonly PdfiumEngine _engine = new();

    [Fact]
    public async Task Second_request_is_served_from_cache()
    {
        var path = TestPdf.Create(_temp.Path, 2);
        var cache = new PagePreviewCache();
        var service = new PagePreviewService(_engine, cache);

        var first = await service.GetPageAsync(path, 1, 400, CancellationToken.None);
        var second = await service.GetPageAsync(path, 1, 400, CancellationToken.None);

        Assert.Same(first, second);
        Assert.Equal(1, cache.Count);
    }

    [Fact]
    public void Cache_evicts_least_recently_used_when_over_budget()
    {
        var cache = new PagePreviewCache(maxBytes: 250);
        var signature = new FileSignature(1, 1);
        RenderedPage Page(int index) => new(index, 3, 10, 10, 40, new byte[100]);

        cache.Add(new PreviewKey("a", signature, 0, 10), Page(0));
        cache.Add(new PreviewKey("a", signature, 1, 10), Page(1));
        Assert.True(cache.TryGet(new PreviewKey("a", signature, 0, 10), out _)); // 0 is now most recent
        cache.Add(new PreviewKey("a", signature, 2, 10), Page(2));

        Assert.True(cache.TryGet(new PreviewKey("a", signature, 0, 10), out _));
        Assert.False(cache.TryGet(new PreviewKey("a", signature, 1, 10), out _));
        Assert.True(cache.CurrentBytes <= 250);
    }

    [Theory]
    [InlineData(1, 200)]
    [InlineData(450, 600)]
    [InlineData(9999, 2400)]
    public void Width_is_bucketed(double requested, int expected) =>
        Assert.Equal(expected, PagePreviewService.BucketWidth(requested));

    public void Dispose()
    {
        _engine.Dispose();
        _temp.Dispose();
    }
}
