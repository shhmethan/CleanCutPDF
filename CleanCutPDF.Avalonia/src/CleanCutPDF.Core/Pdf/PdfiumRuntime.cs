using CleanCutPDF.Core.Pdf.Native;

namespace CleanCutPDF.Core.Pdf;

/// <summary>
/// PDFium has process-global state and is not thread-safe, so the whole
/// process shares exactly one PDF worker thread. The library is initialized
/// once on that thread and left loaded until the process exits.
/// </summary>
internal static class PdfiumRuntime
{
    private static readonly Lazy<PdfWorkerThread> SharedWorker = new(
        () => new PdfWorkerThread(PdfiumNative.FPDF_InitLibrary),
        LazyThreadSafetyMode.ExecutionAndPublication);

    public static PdfWorkerThread Worker => SharedWorker.Value;
}
