using CleanCutPDF.App.Services;
using CleanCutPDF.App.ViewModels;

namespace CleanCutPDF.App.Tests;

/// <summary>Which PDF opens when the one being edited is exported or closed (like closing a browser tab).</summary>
public sealed class NextDocumentTests
{
    private static DocumentItemViewModel Pdf(string name, DocumentLoadState state = DocumentLoadState.Ready) =>
        new($@"C:\scans\{name}.pdf", "Accounting") { State = state };

    [Fact]
    public void The_next_pdf_in_the_list_opens()
    {
        var (a, b, c) = (Pdf("a"), Pdf("b"), Pdf("c"));

        Assert.Same(b, DocumentStore.NextAfter([a, b, c], a, [a]));
        Assert.Same(c, DocumentStore.NextAfter([a, b, c], b, [b]));
    }

    [Fact]
    public void After_the_last_pdf_the_one_before_it_opens()
    {
        var (a, b, c) = (Pdf("a"), Pdf("b"), Pdf("c"));

        Assert.Same(b, DocumentStore.NextAfter([a, b, c], c, [c]));
    }

    [Fact]
    public void Pdfs_that_are_still_loading_failed_or_also_closing_are_skipped()
    {
        var a = Pdf("a");
        var loading = Pdf("loading", DocumentLoadState.Loading);
        var failed = Pdf("failed", DocumentLoadState.Failed);
        var closingToo = Pdf("closing");
        var d = Pdf("d");

        Assert.Same(d, DocumentStore.NextAfter([a, loading, failed, closingToo, d], a, [a, closingToo]));
    }

    [Fact]
    public void Nothing_opens_when_no_other_pdf_is_ready()
    {
        var a = Pdf("a");

        Assert.Null(DocumentStore.NextAfter([a], a, [a]));
        Assert.Null(DocumentStore.NextAfter([a, Pdf("loading", DocumentLoadState.Loading)], a, [a]));
    }
}
