namespace CleanCutPDF.Core.Pdf;

/// <summary>A line of text on a generated page. Coordinates are PDF points from the bottom-left.</summary>
public sealed record PdfTextRun(string Text, double X, double Y, float Size, bool Bold = false, bool CenterX = false, byte Gray = 0);

/// <summary>A filled rectangle on a generated page.</summary>
public sealed record PdfRect(double X, double Y, double Width, double Height, byte R, byte G, byte B);

public sealed record PdfPageSpec(double Width, double Height, IReadOnlyList<PdfRect> Rects, IReadOnlyList<PdfTextRun> Texts);

/// <summary>The printable SPLIT HERE separator sheet (1.x download_split_here_sheet).</summary>
public static class SplitHereTemplate
{
    public const double LetterWidth = 612;
    public const double LetterHeight = 792;

    /// <summary>
    /// One US Letter page with large centered SPLIT HERE text. The size and
    /// position fit the visual detector (a short, wide band of text near the
    /// middle), so a scan of this sheet printed on colored paper is recognized
    /// even when the scanner adds no text layer. <paramref name="background"/>
    /// fills the page (tests use it to simulate colored paper).
    /// </summary>
    public static PdfPageSpec Create((byte R, byte G, byte B)? background = null)
    {
        var rects = background is { } c
            ? new[] { new PdfRect(0, 0, LetterWidth, LetterHeight, c.R, c.G, c.B) }
            : [];
        return new PdfPageSpec(LetterWidth, LetterHeight, rects,
        [
            new PdfTextRun("SPLIT HERE", 0, LetterHeight / 2 - 22, 64, Bold: true, CenterX: true),
            new PdfTextRun("Print on brightly colored paper and place this sheet between documents.", 0, 44, 10,
                CenterX: true, Gray: 140),
            new PdfTextRun("CleanCutPDF splits the scan wherever this page appears and leaves it out of the saved files.", 0, 30, 10,
                CenterX: true, Gray: 140)
        ]);
    }
}
