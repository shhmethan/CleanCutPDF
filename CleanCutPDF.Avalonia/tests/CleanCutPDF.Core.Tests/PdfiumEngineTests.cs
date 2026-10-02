using CleanCutPDF.Core.Models;
using CleanCutPDF.Core.Pdf;

namespace CleanCutPDF.Core.Tests;

public sealed class PdfiumEngineTests : IDisposable
{
    private readonly TempDirectory _temp = new();
    private readonly PdfiumEngine _engine = new();

    [Fact]
    public async Task Open_reports_page_count()
    {
        var path = TestPdf.Create(_temp.Path, 3);

        var info = await _engine.OpenAsync(path);

        Assert.Equal(3, info.PageCount);
        Assert.Equal(Path.GetFullPath(path), info.Path);
    }

    [Fact]
    public async Task Render_produces_white_page_with_black_square()
    {
        var path = TestPdf.Create(_temp.Path, 1);

        var page = await _engine.RenderPageAsync(path, 0, 612);

        Assert.Equal(612, page.Width);
        Assert.Equal(792, page.Height); // US Letter aspect ratio
        Assert.Equal(255, PixelAt(page, 10, 10).B); // margin is white
        Assert.True(PixelAt(page, 144, 144).B < 40); // inside the square is black
    }

    [Fact]
    public async Task Invalid_file_gives_friendly_error()
    {
        var path = Path.Combine(_temp.Path, "broken.pdf");
        await File.WriteAllTextAsync(path, "this is not a pdf");

        var error = await Assert.ThrowsAsync<PdfOpenException>(() => _engine.OpenAsync(path));

        Assert.Contains("broken.pdf", error.Message);
    }

    [Fact]
    public async Task Cancelled_render_does_not_run()
    {
        var path = TestPdf.Create(_temp.Path, 1);
        using var cts = new CancellationTokenSource();
        await cts.CancelAsync();

        await Assert.ThrowsAnyAsync<OperationCanceledException>(
            () => _engine.RenderPageAsync(path, 0, 400, cancellationToken: cts.Token));
    }

    [Fact]
    public async Task Changed_file_is_reopened()
    {
        var path = TestPdf.Create(_temp.Path, 2);
        Assert.Equal(2, (await _engine.OpenAsync(path)).PageCount);

        TestPdf.Create(_temp.Path, 5);
        // Ensure the timestamp moves even on coarse file systems.
        File.SetLastWriteTimeUtc(path, DateTime.UtcNow.AddSeconds(5));

        Assert.Equal(5, (await _engine.OpenAsync(path)).PageCount);
    }

    [Fact]
    public async Task Opened_file_is_not_locked()
    {
        var path = TestPdf.Create(_temp.Path, 1);
        await _engine.OpenAsync(path);

        // Rename-in-place must work while the document is open in the app.
        var renamed = Path.Combine(_temp.Path, "renamed.pdf");
        File.Move(path, renamed);

        Assert.True(File.Exists(renamed));
    }

    private static (byte B, byte G, byte R) PixelAt(RenderedPage page, int x, int y)
    {
        var offset = y * page.Stride + x * 4;
        return (page.Pixels[offset], page.Pixels[offset + 1], page.Pixels[offset + 2]);
    }

    public void Dispose()
    {
        _engine.Dispose();
        _temp.Dispose();
    }
}
