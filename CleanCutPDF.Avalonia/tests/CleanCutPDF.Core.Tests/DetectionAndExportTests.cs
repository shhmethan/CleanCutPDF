using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.Export;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Naming;
using CleanCutPDF.Core.Pdf;
using CleanCutPDF.Core.Workspaces;

namespace CleanCutPDF.Core.Tests;

public sealed class DetectionAndExportTests : IAsyncDisposable
{
    private readonly TempDirectory _temp = new();
    private readonly PdfiumEngine _engine = new();
    private readonly AppPaths _paths;
    private readonly AppLog _log;

    public DetectionAndExportTests()
    {
        _paths = new AppPaths(Path.Combine(_temp.Path, "data"), Path.Combine(_temp.Path, "legacy"));
        _log = new AppLog(_paths);
    }

    /// <summary>p1 p2 [SPLIT HERE text] p4 [colored separator, no text] p6 [blank] p8</summary>
    private string ScanBatch() => RawPdf.Write(_temp.Path, "batch.pdf",
        RawPdf.Text("Client letter page 1"),
        RawPdf.Text("Client letter page 2"),
        RawPdf.Text("SPLIT HERE", 48, 150, 400),
        RawPdf.Text("Notice page 1"),
        RawPdf.ColoredSeparatorWithoutText,
        RawPdf.Text("Statement page 1"),
        RawPdf.Blank,
        RawPdf.Text("Statement page 3"));

    [Theory]
    [InlineData("SPLIT HERE", true)]
    [InlineData("split\nhere", true)]
    [InlineData("S P L I T - H E R E", true)]
    [InlineData("here we split", true)]
    [InlineData("Splitting here", false)]
    [InlineData("Please sign here", false)]
    [InlineData("", false)]
    public void Marker_text_rules_match_1x(string text, bool expected) =>
        Assert.Equal(expected, SplitDetector.IsMarkerText(text));

    [Theory]
    [InlineData(new int[0], 5, "1-5")]
    [InlineData(new[] { 2 }, 5, "1-2,4-5")]
    [InlineData(new[] { 0 }, 3, "2-3")]
    [InlineData(new[] { 1, 2 }, 5, "1-1,4-5")]
    [InlineData(new[] { 4 }, 5, "1-4")]
    [InlineData(new[] { 0 }, 1, "1-1")] // only a marker: whole document as one part (1.x)
    public void Ranges_from_markers(int[] markers, int pages, string expected) =>
        Assert.Equal(expected, string.Join(",", SplitDetector.RangesFromMarkers(markers, pages)));

    [Fact]
    public async Task Detects_text_and_image_only_markers_with_progress()
    {
        var path = ScanBatch();
        var reports = new List<DetectionProgress>();

        var result = await new SplitDetector(_engine, _log).DetectAsync(path, new SyncProgress<DetectionProgress>(reports.Add));

        Assert.Equal([2, 4], result.MarkerPages);
        Assert.Equal("1-2,4-4,6-8", string.Join(",", result.Ranges));
        Assert.Equal(8, reports.Count);
        Assert.Equal(new DetectionProgress(8, 8), reports[^1]);
    }

    [Fact]
    public async Task White_page_with_dark_band_is_not_a_marker()
    {
        var path = RawPdf.Write(_temp.Path, "white.pdf", RawPdf.Text("A"), RawPdf.WhitePageWithDarkBand, RawPdf.Text("B"));

        var result = await new SplitDetector(_engine).DetectAsync(path);

        Assert.Empty(result.MarkerPages);
        Assert.True(result.NoMarkersInMultiPageDocument);
    }

    [Fact]
    public async Task Detection_can_be_cancelled()
    {
        var path = ScanBatch();
        using var cts = new CancellationTokenSource();
        var progress = new SyncProgress<DetectionProgress>(p =>
        {
            if (p.PagesDone == 2)
            {
                cts.Cancel();
            }
        });

        await Assert.ThrowsAnyAsync<OperationCanceledException>(
            () => new SplitDetector(_engine).DetectAsync(path, progress, cts.Token));
    }

    [Fact]
    public async Task Blank_page_detection()
    {
        var path = RawPdf.Write(_temp.Path, "blank.pdf", RawPdf.Blank, RawPdf.Text("Hello world"), RawPdf.SmallBox);
        var detector = new BlankPageDetector(_engine);

        Assert.True(await detector.IsBlankAsync(path, 0));
        Assert.False(await detector.IsBlankAsync(path, 1));
        Assert.False(await detector.IsBlankAsync(path, 2));
    }

    [Fact]
    public async Task Extracted_pages_form_a_valid_pdf()
    {
        var path = ScanBatch();

        var bytes = await _engine.ExtractPagesAsync(path, [0, 1, 7]);
        var output = Path.Combine(_temp.Path, "out.pdf");
        await File.WriteAllBytesAsync(output, bytes);

        Assert.Equal(3, (await _engine.OpenAsync(output)).PageCount);
        Assert.Contains("page 3", await _engine.ExtractPageTextAsync(output, 2));
    }

    [Fact]
    public async Task Export_splits_names_removes_blanks_and_logs_like_1x()
    {
        var path = ScanBatch();
        var detection = await new SplitDetector(_engine).DetectAsync(path);
        var workspace = WorkspaceCatalog.CreateDefault().Resolve("Accounting");
        var parts = new[]
        {
            new PartInput(detection.Ranges[0], new PartValues { ["revoked"] = "true", ["agency"] = "i", ["description"] = "POA", ["date"] = "082026" }),
            new PartInput(detection.Ranges[1], new PartValues { ["revoked"] = "false", ["agency"] = "f", ["description"] = "notice", ["date"] = "" }),
            new PartInput(detection.Ranges[2], new PartValues { ["revoked"] = "false", ["agency"] = "", ["description"] = "inv", ["date"] = "1-5-2026" })
        };
        var output = Path.Combine(_temp.Path, "exports");
        var service = new ExportService(_engine, new ExportHistory(_paths), _log,
            new FakeClock(new DateTimeOffset(2026, 10, 2, 9, 30, 0, TimeSpan.Zero)));
        var request = new ExportRequest(path, workspace, "john smith", parts, output, MakeClientFolder: true, RemoveBlankPages: true);

        var result = await service.ExportAsync(request);

        Assert.Equal(Path.Combine(output, "John Smith"), result.OutputFolder);
        Assert.Equal(
            ["John Smith_Revoked_IRS POA_8-20-2026.pdf", "John Smith_FTB Notice.pdf", "John Smith_Invoice_1-05-2026.pdf"],
            result.Files.Select(f => Path.GetFileName(f.Path)));
        Assert.Equal(2, (await _engine.OpenAsync(result.Files[2].Path)).PageCount); // blank page 7 removed
        Assert.Equal([7], result.Files[2].SkippedPages);

        var history = await File.ReadAllLinesAsync(_paths.ExportHistoryFile);
        Assert.Equal(
            "[2026-10-02 09:30:00] Workspace: Accounting | Client: John Smith | File: John Smith_Revoked_IRS POA_8-20-2026.pdf | " +
            "Pages: 1-2 | Skipped: None | Agency: IRS | Desc: POA | Date: 8-20-2026 | Revoked: True | Matter:  | " +
            "Document Type:  | Fields: Revoked=Revoked; Agency Code=IRS; Description=POA; Date=8-20-2026",
            history[0]);
        Assert.Contains("Skipped: [7]", history[2]);

        // Exporting again never overwrites.
        var again = await service.ExportAsync(request);
        Assert.Equal("John Smith_Revoked_IRS POA_8-20-2026_2.pdf", Path.GetFileName(again.Files[0].Path));
    }

    [Fact]
    public async Task Cancelled_export_leaves_no_partial_files()
    {
        var path = ScanBatch();
        var workspace = WorkspaceCatalog.CreateDefault().Resolve("Legal");
        var parts = SplitDetector.RangesFromMarkers([2, 4], 8)
            .Select(r => new PartInput(r, new PartValues { ["description"] = $"Doc {r.Start}" })).ToList();
        var output = Path.Combine(_temp.Path, "cancelled");
        using var cts = new CancellationTokenSource();
        var progress = new SyncProgress<ExportProgress>(p =>
        {
            if (p.PartsDone == 2)
            {
                cts.Cancel();
            }
        });

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            new ExportService(_engine, new ExportHistory(_paths), _log).ExportAsync(
                new ExportRequest(path, workspace, "", parts, output, false, false), progress, cts.Token));

        Assert.Empty(Directory.GetFiles(output));
        Assert.False(File.Exists(_paths.ExportHistoryFile));
    }

    [Fact]
    public void Validation_reports_like_1x()
    {
        var catalog = WorkspaceCatalog.CreateDefault();
        catalog.Fields["agency"].Required = true;
        var workspace = catalog.Resolve("Accounting");
        var today = new DateOnly(2026, 10, 2);
        var range = new PageRange(0, 0);

        var check = ExportValidator.Check(workspace,
        [
            new PartInput(range, new PartValues { ["agency"] = "", ["date"] = "" }),
            new PartInput(range, new PartValues { ["agency"] = "i", ["date"] = "12-25-2026" })
        ], today);

        Assert.False(check.CanExport);
        Assert.Equal(["Part 1: Agency Code"], check.MissingRequired);
        Assert.Equal(["Part 1: Date"], check.BlankOptionalDates);
        Assert.Equal(["Part 2: Date (12-25-2026)"], check.FutureDates);

        var invalid = ExportValidator.Check(workspace, [new PartInput(range, new PartValues { ["agency"] = "i", ["date"] = "99/99/9999" })], today);
        Assert.StartsWith("Part 1 — Date:", invalid.InvalidValue);
    }

    public async ValueTask DisposeAsync()
    {
        _engine.Dispose();
        await _log.DisposeAsync();
        _temp.Dispose();
    }
}

/// <summary>IProgress that reports synchronously (Progress&lt;T&gt; posts to the thread pool).</summary>
internal sealed class SyncProgress<T>(Action<T> report) : IProgress<T>
{
    public void Report(T value) => report(value);
}
