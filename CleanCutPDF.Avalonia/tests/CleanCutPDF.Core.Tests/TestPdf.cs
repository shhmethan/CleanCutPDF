using PdfSharp.Drawing;
using PdfSharp.Pdf;

namespace CleanCutPDF.Core.Tests;

/// <summary>Creates small throwaway PDFs for tests.</summary>
internal static class TestPdf
{
    public static string Create(string directory, int pageCount, string fileName = "sample.pdf")
    {
        Directory.CreateDirectory(directory);
        var path = Path.Combine(directory, fileName);
        using var document = new PdfDocument();
        for (var i = 0; i < pageCount; i++)
        {
            var page = document.AddPage();
            using var graphics = XGraphics.FromPdfPage(page);
            // A solid black square so rendering can be verified without fonts.
            graphics.DrawRectangle(XBrushes.Black, 72, 72, 144, 144);
        }

        document.Save(path);
        return path;
    }
}

public sealed class TempDirectory : IDisposable
{
    public string Path { get; } =
        System.IO.Path.Combine(System.IO.Path.GetTempPath(), "cleancut-tests-" + Guid.NewGuid().ToString("N"));

    public TempDirectory() => Directory.CreateDirectory(Path);

    public void Dispose()
    {
        try
        {
            Directory.Delete(Path, recursive: true);
        }
        catch
        {
            // Temp cleanup is best effort.
        }
    }
}
