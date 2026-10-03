using System.Text.RegularExpressions;
using System.Text.Json.Serialization;
using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.Models;

namespace CleanCutPDF.Core.Pdf;

/// <summary>An inclusive, 0-based page range (Python's {"start", "end"}).</summary>
public sealed record PageRange([property: JsonPropertyName("start")] int Start, [property: JsonPropertyName("end")] int End)
{
    public int PageCount => End - Start + 1;
    public override string ToString() => $"{Start + 1}-{End + 1}";
}

public sealed record SplitDetectionResult(IReadOnlyList<PageRange> Ranges, IReadOnlyList<int> MarkerPages, int PageCount)
{
    /// <summary>1.x showed a warning when a multi-page PDF had no markers.</summary>
    public bool NoMarkersInMultiPageDocument => MarkerPages.Count == 0 && PageCount > 1;
}

public readonly record struct DetectionProgress(int PagesDone, int PageCount);

/// <summary>
/// Finds SPLIT HERE separator pages and turns them into Part ranges.
///
/// Same rules as 1.x: a page is a marker when its text contains SPLITHERE
/// (letters only) or both words SPLIT and HERE. Pages with no text layer get a
/// conservative visual check for the printed colored separator sheet. Unlike
/// 1.x this runs off the UI thread, reports progress, can be cancelled, and
/// uses low priority so page previews stay instant while it works.
/// </summary>
public sealed partial class SplitDetector(IPdfEngine engine, AppLog? log = null)
{
    public async Task<SplitDetectionResult> DetectAsync(string path, IProgress<DetectionProgress>? progress = null,
        CancellationToken cancellationToken = default)
    {
        var info = await engine.OpenAsync(path, cancellationToken);
        var markers = new List<int>();
        var started = System.Diagnostics.Stopwatch.GetTimestamp();

        for (var index = 0; index < info.PageCount; index++)
        {
            cancellationToken.ThrowIfCancellationRequested();
            var page = await engine.AnalyzePageAsync(info.Path, index, PdfWorkPriority.Low, cancellationToken);
            var isMarker = IsMarkerText(page.Text);
            var source = "text";

            if (!isMarker && string.IsNullOrWhiteSpace(page.Text))
            {
                // Expensive path, only for scans without an OCR/text layer.
                var image = await engine.RenderPageSizedAsync(info.Path, index, VisualWidth, VisualHeight,
                    grayscale: false, PdfWorkPriority.Low, cancellationToken);
                isMarker = LooksLikeVisualMarker(image);
                source = "visual check";
            }

            if (isMarker)
            {
                markers.Add(index);
                log?.Debug("Split", $"{Path.GetFileName(path)}: marker on page {index + 1} ({source})");
            }

            progress?.Report(new DetectionProgress(index + 1, info.PageCount));
        }

        var ranges = RangesFromMarkers(markers, info.PageCount);
        log?.Info("Split", $"{Path.GetFileName(path)}: {markers.Count} marker(s), {ranges.Count} part(s), " +
                           $"{info.PageCount} page(s) in {System.Diagnostics.Stopwatch.GetElapsedTime(started).TotalMilliseconds:N0} ms");
        return new SplitDetectionResult(ranges, markers, info.PageCount);
    }

    public static bool IsMarkerText(string? text)
    {
        var upper = (text ?? "").ToUpperInvariant();
        if (NonLetters().Replace(upper, "").Contains("SPLITHERE", StringComparison.Ordinal))
        {
            return true;
        }

        var words = Words().Matches(upper).Select(m => m.Value).ToHashSet();
        return words.Contains("SPLIT") && words.Contains("HERE");
    }

    /// <summary>Pages between markers; marker pages are dropped; no markers → the whole PDF is one part.</summary>
    public static IReadOnlyList<PageRange> RangesFromMarkers(IReadOnlyList<int> markers, int pageCount)
    {
        var ranges = new List<PageRange>();
        var start = 0;
        foreach (var marker in markers.Order())
        {
            if (start <= marker - 1)
            {
                ranges.Add(new PageRange(start, marker - 1));
            }

            start = marker + 1;
        }

        if (start < pageCount)
        {
            ranges.Add(new PageRange(start, pageCount - 1));
        }

        if (ranges.Count == 0)
        {
            ranges.Add(new PageRange(0, Math.Max(0, pageCount - 1)));
        }

        return ranges;
    }

    // 1.x rendered at 65% and resized to 240×312 before analysing.
    internal const int VisualWidth = 240;
    internal const int VisualHeight = 312;

    /// <summary>
    /// Recognizes the colored SPLIT HERE sheet on an image-only page: a nearly
    /// uniform colored background with one short, wide band of dark text near
    /// the center. Thresholds are identical to 1.x.
    /// </summary>
    public static bool LooksLikeVisualMarker(RenderedPage image)
    {
        var width = image.Width;
        var height = image.Height;
        var total = width * height;
        if (total == 0)
        {
            return false;
        }

        // Per-channel median (PIL ImageStat semantics).
        var histograms = new int[3, 256];
        ForEachPixel(image, (_, _, r, g, b) =>
        {
            histograms[0, r]++;
            histograms[1, g]++;
            histograms[2, b]++;
        });
        var median = new int[3];
        for (var channel = 0; channel < 3; channel++)
        {
            int cumulative = 0, half = total / 2;
            for (var level = 0; level < 256; level++)
            {
                cumulative += histograms[channel, level];
                if (cumulative > half)
                {
                    median[channel] = level;
                    break;
                }
            }
        }

        var backgroundRange = median.Max() - median.Min();
        var brightness = median.Sum() / 3.0;
        if (!(backgroundRange >= 15 || brightness <= 238))
        {
            return false; // White office paper.
        }

        int uniform = 0, dark = 0;
        ForEachPixel(image, (_, _, r, g, b) =>
        {
            if (Math.Abs(r - median[0]) <= 30 && Math.Abs(g - median[1]) <= 30 && Math.Abs(b - median[2]) <= 30)
            {
                uniform++;
            }

            if (Math.Max(r, Math.Max(g, b)) < 120)
            {
                dark++;
            }
        });
        if ((double)uniform / total < 0.82 || (double)dark / total > 0.025)
        {
            return false;
        }

        int left = (int)(width * 0.15), right = (int)(width * 0.85);
        int top = (int)(height * 0.20), bottom = (int)(height * 0.80);
        int count = 0, minX = int.MaxValue, maxX = -1, minY = int.MaxValue, maxY = -1;
        ForEachPixel(image, (x, y, r, g, b) =>
        {
            if (x < left || x >= right || y < top || y >= bottom || Math.Max(r, Math.Max(g, b)) >= 120)
            {
                return;
            }

            count++;
            minX = Math.Min(minX, x);
            maxX = Math.Max(maxX, x);
            minY = Math.Min(minY, y);
            maxY = Math.Max(maxY, y);
        });
        if (count < 70)
        {
            return false;
        }

        var textWidth = (maxX - minX + 1) / (double)width;
        var textHeight = (maxY - minY + 1) / (double)height;
        var centerY = (minY + maxY) / 2.0 / height;
        return textWidth is >= 0.25 and <= 0.72
               && textHeight is >= 0.015 and <= 0.13
               && centerY is >= 0.32 and <= 0.68;
    }

    internal static void ForEachPixel(RenderedPage image, Action<int, int, int, int, int> visit)
    {
        var pixels = image.Pixels;
        for (var y = 0; y < image.Height; y++)
        {
            var row = y * image.Stride;
            for (var x = 0; x < image.Width; x++)
            {
                var i = row + x * 4;
                visit(x, y, pixels[i + 2], pixels[i + 1], pixels[i]); // BGRA → r, g, b
            }
        }
    }

    [GeneratedRegex("[^A-Z]")]
    private static partial Regex NonLetters();

    [GeneratedRegex("[A-Z0-9]+")]
    private static partial Regex Words();
}
