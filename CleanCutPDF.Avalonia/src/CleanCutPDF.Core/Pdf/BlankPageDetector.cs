using CleanCutPDF.Core.Models;

namespace CleanCutPDF.Core.Pdf;

/// <summary>
/// Decides whether a page is confidently blank (1.x is_blank_page). Pages with
/// four or more letters/digits of text, or any annotation, are always kept.
/// Otherwise a small grayscale render is checked for ink, ignoring a thin
/// margin where scanner shadows appear. Uncertain pages are kept.
/// </summary>
public sealed class BlankPageDetector(IPdfEngine engine)
{
    private const double RenderScale = 0.35;
    private const int MaxWidth = 240;
    private const int MaxHeight = 320;

    public async Task<bool> IsBlankAsync(string path, int pageIndex, CancellationToken cancellationToken = default)
    {
        var page = await engine.AnalyzePageAsync(path, pageIndex, PdfWorkPriority.High, cancellationToken);
        if (page.Text.Count(char.IsAsciiLetterOrDigit) >= 4 || page.AnnotationCount > 0)
        {
            return false;
        }

        var scale = Math.Min(RenderScale, Math.Min(MaxWidth / Math.Max(1f, page.WidthPoints), MaxHeight / Math.Max(1f, page.HeightPoints)));
        var width = Math.Max(8, (int)Math.Round(page.WidthPoints * scale));
        var height = Math.Max(8, (int)Math.Round(page.HeightPoints * scale));
        var image = await engine.RenderPageSizedAsync(path, pageIndex, width, height, grayscale: true,
            PdfWorkPriority.High, cancellationToken);
        return LooksBlank(image);
    }

    public static bool LooksBlank(RenderedPage image)
    {
        int left = 0, top = 0, right = image.Width, bottom = image.Height;
        if (image.Width > 20 && image.Height > 20)
        {
            var mx = Math.Max(2, (int)(image.Width * 0.025));
            var my = Math.Max(2, (int)(image.Height * 0.025));
            (left, top, right, bottom) = (mx, my, image.Width - mx, image.Height - my);
        }

        var histogram = new long[256];
        long total = 0;
        SplitDetector.ForEachPixel(image, (x, y, r, g, b) =>
        {
            if (x < left || x >= right || y < top || y >= bottom)
            {
                return;
            }

            histogram[(r * 299 + g * 587 + b * 114) / 1000]++;
            total++;
        });
        if (total == 0)
        {
            return false;
        }

        // Background = the level that 90% of pixels are at or below.
        long cumulative = 0;
        var background = 255;
        for (var level = 0; level < 256; level++)
        {
            cumulative += histogram[level];
            if (cumulative >= total * 0.90)
            {
                background = level;
                break;
            }
        }

        double Below(int cutoff) => cutoff <= 0 ? 0 : histogram.Take(cutoff).Sum() / (double)total;

        var lightInk = Below(Math.Max(0, background - 12));
        var darkInk = Below(Math.Max(0, background - 35));
        var veryDarkInk = Below(Math.Max(0, background - 70));
        return background >= 225 && lightInk <= 0.012 && darkInk <= 0.003 && veryDarkInk <= 0.001;
    }
}
