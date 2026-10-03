using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.Export;
using CleanCutPDF.Core.History;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Pdf;

namespace CleanCutPDF.Core.Tests;

/// <summary>Records what would be recycled without touching the real Recycle Bin.</summary>
internal sealed class FakeRecycleBin : IRecycleBin
{
    public List<string> Recycled { get; } = [];

    public string? Recycle(string path)
    {
        if (!File.Exists(path))
        {
            return "it no longer exists";
        }

        File.Delete(path);
        Recycled.Add(path);
        return null;
    }
}

public sealed class Phase4Tests : IAsyncDisposable
{
    private const string NewLine =
        "[2026-10-02 09:30:00] Workspace: Accounting | Client: John Smith | File: John Smith_IRS POA.pdf | Pages: 1-2 | " +
        "Skipped: [2] | Agency: IRS | Desc: POA | Date: 8-20-2026 | Revoked: True | Matter:  | Document Type:  | " +
        "Fields: Agency Code=IRS; Description=POA";

    // A 1.x line written before workspaces existed.
    private const string OldLine =
        "[2025-07-01 14:05:09] Client: Acme LLC | File: Acme LLC_FTB Notice.pdf | Pages: 4-4 | Skipped: None | " +
        "Agency: FTB | Desc: Notice | Date: None | Revoked: False";

    private readonly TempDirectory _temp = new();
    private readonly PdfiumEngine _engine = new();
    private readonly AppPaths _paths;
    private readonly AppLog _log;

    public Phase4Tests()
    {
        _paths = new AppPaths(Path.Combine(_temp.Path, "data"), Path.Combine(_temp.Path, "legacy"));
        _log = new AppLog(_paths);
    }

    private static IReadOnlyList<HistoryEntry> Sample() => HistoryLog.Parse(
    [
        OldLine,
        "[2026-10-02 08:00:00] Export folder changed from 'a' to 'b'",
        NewLine,
        NewLine.Replace("09:30:00", "11:00:00").Replace("POA.pdf", "POA_2.pdf"),
        NewLine.Replace("John Smith", "Bob Lee").Replace("Accounting", "Legal").Replace("2026-10-02", "2026-09-15")
    ]);

    [Fact]
    public void Parses_new_and_1x_lines_and_skips_non_entries()
    {
        var entries = Sample();

        Assert.Equal(4, entries.Count);
        var first = entries[0];
        Assert.Equal("Acme LLC", first.Client);
        Assert.Equal("", first.Workspace);
        Assert.Equal("2025-07-01", first.ExportDate);
        var entry = entries[1];
        Assert.Equal(("Accounting", "John Smith", "John Smith_IRS POA.pdf", "1-2", "[2]", "IRS", "POA", "8-20-2026"),
            (entry.Workspace, entry.Client, entry.File, entry.Pages, entry.Skipped, entry.Agency, entry.Description, entry.DocumentDate));
        Assert.True(entry.Revoked);
        Assert.Contains("blank pages removed: 2", entry.Details);
    }

    [Fact]
    public void Search_filters_sort_and_group()
    {
        var entries = Sample();

        Assert.Equal(2, HistoryLog.Filter(entries, new HistoryFilter(Search: "john smith")).Count); // case-insensitive
        Assert.Single(HistoryLog.Filter(entries, new HistoryFilter(Workspace: "leg")));
        Assert.Equal(2, HistoryLog.Filter(entries, new HistoryFilter(From: new DateOnly(2026, 10, 1))).Count);
        Assert.Single(HistoryLog.Filter(entries, new HistoryFilter(To: new DateOnly(2025, 12, 31))));

        var newest = HistoryLog.Filter(entries, new HistoryFilter());
        Assert.Equal("John Smith_IRS POA_2.pdf", newest[0].File);
        Assert.Equal(["Acme LLC", "Bob Lee", "John Smith", "John Smith"],
            HistoryLog.Filter(entries, new HistoryFilter(Sort: HistorySort.ClientAToZ)).Select(e => e.Client));

        var groups = HistoryLog.Group(newest);
        Assert.Equal(3, groups.Count);
        Assert.Equal("John Smith – 2026-10-02", groups[0].Heading);
        Assert.Equal(2, groups[0].Entries.Count);
    }

    [Theory]
    [InlineData(HistoryExportFormat.Csv, "Export Date,Client,File,Pages")]
    [InlineData(HistoryExportFormat.Tsv, "Export Date\tClient\tFile\tPages")]
    [InlineData(HistoryExportFormat.Txt, "Export Date: 2025-07-01 | Client: Acme LLC")]
    [InlineData(HistoryExportFormat.Html, "<td>John Smith_IRS POA.pdf</td>")]
    public async Task Text_exports_contain_the_entries(HistoryExportFormat format, string expected)
    {
        var bytes = await HistoryLog.ExportAsync(Sample(), format, _engine);
        var text = System.Text.Encoding.UTF8.GetString(bytes);

        Assert.Contains(expected, text);
        if (format == HistoryExportFormat.Csv)
        {
            Assert.Contains("=\"\"1-2\"\"", text); // pages kept as text for Excel, quoted for CSV
        }
    }

    [Fact]
    public async Task Pdf_export_is_a_readable_pdf()
    {
        var path = Path.Combine(_temp.Path, "history.pdf");
        await File.WriteAllBytesAsync(path, await HistoryLog.ExportAsync(Sample(), HistoryExportFormat.Pdf, _engine));

        Assert.Equal(1, (await _engine.OpenAsync(path)).PageCount);
        var text = await _engine.ExtractPageTextAsync(path, 0);
        Assert.Contains("John Smith_IRS POA.pdf", text);
        Assert.Contains("4 entries", text);
    }

    [Fact]
    public async Task Long_history_spans_several_pdf_pages()
    {
        var many = Enumerable.Range(0, 120).Select(_ => Sample()[1]).ToList();
        var path = Path.Combine(_temp.Path, "long.pdf");
        await File.WriteAllBytesAsync(path, await HistoryLog.ExportAsync(many, HistoryExportFormat.Pdf, _engine));

        Assert.True((await _engine.OpenAsync(path)).PageCount >= 3);
    }

    [Fact]
    public async Task Split_here_template_is_detected_by_text_and_as_an_image_only_scan()
    {
        var white = Path.Combine(_temp.Path, "template.pdf");
        await File.WriteAllBytesAsync(white, await _engine.CreateDocumentAsync([SplitHereTemplate.Create()]));
        Assert.True(SplitDetector.IsMarkerText(await _engine.ExtractPageTextAsync(white, 0)));

        // Printed on yellow paper and scanned without OCR: only the picture is available.
        var yellow = Path.Combine(_temp.Path, "template-yellow.pdf");
        await File.WriteAllBytesAsync(yellow, await _engine.CreateDocumentAsync([SplitHereTemplate.Create((255, 230, 80))]));
        var image = await _engine.RenderPageSizedAsync(yellow, 0, SplitDetector.VisualWidth, SplitDetector.VisualHeight,
            grayscale: false, PdfWorkPriority.High);
        Assert.True(SplitDetector.LooksLikeVisualMarker(image));
    }

    [Fact]
    public async Task Undo_recycles_files_removes_empty_client_folder_and_notes_it()
    {
        var folder = Path.Combine(_temp.Path, "out", "John Smith");
        Directory.CreateDirectory(folder);
        var files = new[] { Path.Combine(folder, "a.pdf"), Path.Combine(folder, "b.pdf") };
        foreach (var file in files)
        {
            await File.WriteAllTextAsync(file, "x");
        }

        var bin = new FakeRecycleBin();
        var history = new ExportHistory(_paths, bin);
        var result = await new ExportUndo(bin, history, _log).UndoAsync([.. files, Path.Combine(folder, "gone.pdf")]);

        Assert.Equal(2, result.Recycled);
        Assert.Single(result.Problems);
        Assert.Equal(files, bin.Recycled);
        Assert.False(Directory.Exists(folder));
        Assert.All(await history.ReadLinesAsync(), line => Assert.Contains("to the Recycle Bin", line));
        Assert.Empty(HistoryLog.Parse(await history.ReadLinesAsync())); // undo notes are not entries
    }

    [Fact]
    public async Task Clear_log_sends_history_to_recycle_bin_and_raises_changed()
    {
        var bin = new FakeRecycleBin();
        var history = new ExportHistory(_paths, bin);
        await history.AppendAsync([NewLine]);
        var changed = 0;
        history.Changed += (_, _) => changed++;

        Assert.Null(await history.ClearAsync());

        Assert.Single(bin.Recycled);
        Assert.False(File.Exists(history.FilePath));
        Assert.Empty(await history.ReadLinesAsync());
        Assert.Equal(1, changed);
    }

    public async ValueTask DisposeAsync()
    {
        _engine.Dispose();
        await _log.DisposeAsync();
        _temp.Dispose();
    }
}
