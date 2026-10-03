using System.Text;

namespace CleanCutPDF.Core.Tests;

/// <summary>
/// Writes minimal, valid PDFs from page content streams using the built-in
/// Helvetica font, so tests control exactly what is on each page.
/// </summary>
internal static class RawPdf
{
    public static string Text(string text, int size = 20, int x = 72, int y = 700) =>
        $"BT /F1 {size} Tf {x} {y} Td ({text}) Tj ET";

    public const string Blank = "";

    /// <summary>Image-only colored SPLIT HERE sheet: yellow page with a dark centered band, no text layer.</summary>
    public const string ColoredSeparatorWithoutText = "1 0.9 0.3 rg 0 0 612 792 re f 0 0 0 rg 180 380 260 40 re f";

    public const string WhitePageWithDarkBand = "0 0 0 rg 180 380 260 40 re f";

    public const string SmallBox = "0 0 0 rg 100 100 200 150 re f";

    public static string Write(string directory, string fileName, params string[] pageContents)
    {
        Directory.CreateDirectory(directory);
        var path = Path.Combine(directory, fileName);
        var objects = new List<string>
        {
            "<< /Type /Catalog /Pages 2 0 R >>",
            "", // pages, filled below
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
        };

        var kids = new List<string>();
        foreach (var content in pageContents)
        {
            var pageNumber = objects.Count + 1;
            kids.Add($"{pageNumber} 0 R");
            objects.Add($"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] " +
                        $"/Resources << /Font << /F1 3 0 R >> >> /Contents {pageNumber + 1} 0 R >>");
            objects.Add($"<< /Length {Encoding.ASCII.GetByteCount(content)} >>\nstream\n{content}\nendstream");
        }

        objects[1] = $"<< /Type /Pages /Kids [{string.Join(' ', kids)}] /Count {kids.Count} >>";

        var builder = new StringBuilder("%PDF-1.4\n");
        var offsets = new List<int>();
        for (var i = 0; i < objects.Count; i++)
        {
            offsets.Add(Encoding.ASCII.GetByteCount(builder.ToString()));
            builder.Append($"{i + 1} 0 obj\n{objects[i]}\nendobj\n");
        }

        var xref = Encoding.ASCII.GetByteCount(builder.ToString());
        builder.Append($"xref\n0 {objects.Count + 1}\n0000000000 65535 f \n");
        foreach (var offset in offsets)
        {
            builder.Append($"{offset:D10} 00000 n \n");
        }

        builder.Append($"trailer\n<< /Size {objects.Count + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n");
        File.WriteAllText(path, builder.ToString(), Encoding.ASCII);
        return path;
    }
}
