using System.Runtime.InteropServices;
using CleanCutPDF.Core.Models;
using CleanCutPDF.Core.Pdf.Native;

namespace CleanCutPDF.Core.Pdf;

/// <summary>Raised with a message that is safe to show to the user.</summary>
public sealed class PdfOpenException(string userMessage, Exception? inner = null)
    : Exception(userMessage, inner);

public interface IPdfEngine : IDisposable
{
    /// <summary>Opens (or reuses) a document and returns its page count and file signature.</summary>
    Task<PdfDocumentInfo> OpenAsync(string path, CancellationToken cancellationToken = default);

    /// <summary>Renders one page to BGRA pixels at the requested pixel width.</summary>
    Task<RenderedPage> RenderPageAsync(string path, int pageIndex, int targetWidth,
        PdfWorkPriority priority = PdfWorkPriority.High, CancellationToken cancellationToken = default);

    /// <summary>Extracts the text layer of one page (empty for image-only scans).</summary>
    Task<string> ExtractPageTextAsync(string path, int pageIndex, CancellationToken cancellationToken = default);

    /// <summary>Releases the native handle and file buffer for a document.</summary>
    Task CloseAsync(string path);
}

/// <summary>
/// PDFium-backed engine. Document handles stay open between calls (the Python
/// app re-opened the PDF on every preview page change), and a small LRU limit
/// keeps memory bounded when many files are imported.
/// </summary>
public sealed class PdfiumEngine : IPdfEngine
{
    private const int MaxOpenDocuments = 6;
    private const int MaxRenderDimension = 6000;

    private readonly PdfWorkerThread _worker = PdfiumRuntime.Worker;
    private bool _disposed;

    // Accessed only on the worker thread.
    private readonly Dictionary<string, OpenDocument> _documents = new(StringComparer.OrdinalIgnoreCase);
    private readonly LinkedList<string> _lru = new();

    public async Task<PdfDocumentInfo> OpenAsync(string path, CancellationToken cancellationToken = default)
    {
        var fullPath = Path.GetFullPath(path);
        var signature = FileSignature.TryRead(fullPath)
                        ?? throw new PdfOpenException($"The file could not be found:\n{fullPath}");

        // Fast path: already open with the same signature.
        var existing = await _worker.InvokeAsync(
            () => TryGetCurrent(fullPath, signature), PdfWorkPriority.High, cancellationToken);
        if (existing is not null)
        {
            return existing;
        }

        // File reading happens on the thread pool so the PDF thread stays free.
        byte[] bytes;
        try
        {
            bytes = await File.ReadAllBytesAsync(fullPath, cancellationToken);
        }
        catch (Exception error) when (error is IOException or UnauthorizedAccessException)
        {
            throw new PdfOpenException(
                $"{Path.GetFileName(fullPath)} could not be read. It may be open in another program or you may not have permission.",
                error);
        }

        return await _worker.InvokeAsync(
            () => LoadOnWorker(fullPath, signature, bytes), PdfWorkPriority.High, cancellationToken);
    }

    public async Task<RenderedPage> RenderPageAsync(string path, int pageIndex, int targetWidth,
        PdfWorkPriority priority = PdfWorkPriority.High, CancellationToken cancellationToken = default)
    {
        // A document can be evicted from the LRU between Open and Render when
        // many files are busy at once; reopen it once in that case.
        for (var attempt = 0; ; attempt++)
        {
            var info = await OpenAsync(path, cancellationToken);
            try
            {
                return await _worker.InvokeAsync(
                    () => RenderOnWorker(info.Path, pageIndex, targetWidth, cancellationToken),
                    priority, cancellationToken);
            }
            catch (DocumentNotOpenException) when (attempt == 0)
            {
            }
        }
    }

    public async Task<string> ExtractPageTextAsync(string path, int pageIndex, CancellationToken cancellationToken = default)
    {
        for (var attempt = 0; ; attempt++)
        {
            var info = await OpenAsync(path, cancellationToken);
            try
            {
                return await _worker.InvokeAsync(
                    () => ExtractTextOnWorker(info.Path, pageIndex), PdfWorkPriority.High, cancellationToken);
            }
            catch (DocumentNotOpenException) when (attempt == 0)
            {
            }
        }
    }

    public Task CloseAsync(string path)
    {
        var fullPath = Path.GetFullPath(path);
        return _worker.InvokeAsync(() => CloseOnWorker(fullPath), PdfWorkPriority.High);
    }

    /// <summary>Closes this engine's documents. The shared PDFium thread keeps running.</summary>
    public void Dispose()
    {
        if (_disposed)
        {
            return;
        }

        _disposed = true;
        try
        {
            _worker.InvokeAsync(CloseAll).Wait(TimeSpan.FromSeconds(5));
        }
        catch (AggregateException)
        {
            // Shutting down; nothing useful to report.
        }
    }

    // ───── Worker-thread implementation ─────

    private PdfDocumentInfo? TryGetCurrent(string fullPath, FileSignature signature)
    {
        if (!_documents.TryGetValue(fullPath, out var document))
        {
            return null;
        }

        if (document.Info.Signature != signature)
        {
            // The file changed on disk; drop the stale handle.
            CloseOnWorker(fullPath);
            return null;
        }

        Touch(fullPath);
        return document.Info;
    }

    private PdfDocumentInfo LoadOnWorker(string fullPath, FileSignature signature, byte[] bytes)
    {
        // Another request may have opened it while the bytes were being read.
        var current = TryGetCurrent(fullPath, signature);
        if (current is not null)
        {
            return current;
        }

        var pin = GCHandle.Alloc(bytes, GCHandleType.Pinned);
        var handle = PdfiumNative.FPDF_LoadMemDocument64(pin.AddrOfPinnedObject(), (nuint)bytes.Length, null);
        if (handle == IntPtr.Zero)
        {
            var error = (uint)PdfiumNative.FPDF_GetLastError().Value;
            pin.Free();
            throw new PdfOpenException(DescribeLoadError(Path.GetFileName(fullPath), error));
        }

        var pageCount = PdfiumNative.FPDF_GetPageCount(handle);
        var info = new PdfDocumentInfo(fullPath, pageCount, signature);
        _documents[fullPath] = new OpenDocument(handle, pin, info);
        Touch(fullPath);

        while (_documents.Count > MaxOpenDocuments && _lru.Last is { } oldest)
        {
            CloseOnWorker(oldest.Value);
        }

        return info;
    }

    private RenderedPage RenderOnWorker(string fullPath, int pageIndex, int targetWidth, CancellationToken cancellationToken)
    {
        var document = Get(fullPath);
        var pageCount = document.Info.PageCount;
        if (pageIndex < 0 || pageIndex >= pageCount)
        {
            throw new ArgumentOutOfRangeException(nameof(pageIndex), $"Page {pageIndex + 1} does not exist.");
        }

        cancellationToken.ThrowIfCancellationRequested();

        var page = PdfiumNative.FPDF_LoadPage(document.Handle, pageIndex);
        if (page == IntPtr.Zero)
        {
            throw new PdfOpenException($"Page {pageIndex + 1} could not be loaded.");
        }

        try
        {
            var pageWidth = Math.Max(1f, PdfiumNative.FPDF_GetPageWidthF(page));
            var pageHeight = Math.Max(1f, PdfiumNative.FPDF_GetPageHeightF(page));
            var width = Math.Clamp(targetWidth, 16, MaxRenderDimension);
            var height = Math.Clamp((int)Math.Round(width * pageHeight / pageWidth), 16, MaxRenderDimension);

            var bitmap = PdfiumNative.FPDFBitmap_Create(width, height, 1);
            if (bitmap == IntPtr.Zero)
            {
                throw new PdfOpenException("Not enough memory to render this page.");
            }

            try
            {
                PdfiumNative.FPDFBitmap_FillRect(bitmap, 0, 0, width, height, new CULong(0xFFFFFFFF));
                PdfiumNative.FPDF_RenderPageBitmap(bitmap, page, 0, 0, width, height, 0, PdfiumNative.FPDF_ANNOT);

                var stride = PdfiumNative.FPDFBitmap_GetStride(bitmap);
                var pixels = new byte[stride * height];
                Marshal.Copy(PdfiumNative.FPDFBitmap_GetBuffer(bitmap), pixels, 0, pixels.Length);
                return new RenderedPage(pageIndex, pageCount, width, height, stride, pixels);
            }
            finally
            {
                PdfiumNative.FPDFBitmap_Destroy(bitmap);
            }
        }
        finally
        {
            PdfiumNative.FPDF_ClosePage(page);
        }
    }

    private unsafe string ExtractTextOnWorker(string fullPath, int pageIndex)
    {
        var document = Get(fullPath);
        var page = PdfiumNative.FPDF_LoadPage(document.Handle, pageIndex);
        if (page == IntPtr.Zero)
        {
            return string.Empty;
        }

        try
        {
            var textPage = PdfiumNative.FPDFText_LoadPage(page);
            if (textPage == IntPtr.Zero)
            {
                return string.Empty;
            }

            try
            {
                var count = PdfiumNative.FPDFText_CountChars(textPage);
                if (count <= 0)
                {
                    return string.Empty;
                }

                var buffer = new ushort[count + 1];
                fixed (ushort* pointer = buffer)
                {
                    var written = PdfiumNative.FPDFText_GetText(textPage, 0, count, pointer);
                    var length = Math.Max(0, written - 1); // written includes the terminator
                    return new string((char*)pointer, 0, length);
                }
            }
            finally
            {
                PdfiumNative.FPDFText_ClosePage(textPage);
            }
        }
        finally
        {
            PdfiumNative.FPDF_ClosePage(page);
        }
    }

    private OpenDocument Get(string fullPath)
    {
        if (!_documents.TryGetValue(fullPath, out var document))
        {
            throw new DocumentNotOpenException();
        }

        Touch(fullPath);
        return document;
    }

    private void Touch(string fullPath)
    {
        var node = _lru.Find(fullPath);
        if (node is not null)
        {
            _lru.Remove(node);
        }

        _lru.AddFirst(fullPath);
    }

    private void CloseOnWorker(string fullPath)
    {
        if (_documents.Remove(fullPath, out var document))
        {
            PdfiumNative.FPDF_CloseDocument(document.Handle);
            document.Pin.Free();
        }

        _lru.Remove(fullPath);
    }

    private void CloseAll()
    {
        foreach (var path in _documents.Keys.ToList())
        {
            CloseOnWorker(path);
        }
    }

    private static string DescribeLoadError(string fileName, uint error) => error switch
    {
        PdfiumNative.FPDF_ERR_FILE => $"{fileName} could not be opened.",
        PdfiumNative.FPDF_ERR_FORMAT => $"{fileName} is not a valid PDF or is damaged.",
        PdfiumNative.FPDF_ERR_PASSWORD => $"{fileName} is password protected. Remove the password and try again.",
        PdfiumNative.FPDF_ERR_SECURITY => $"{fileName} uses unsupported security settings.",
        _ => $"{fileName} could not be opened (PDFium error {error})."
    };

    private sealed class DocumentNotOpenException : Exception;

    private sealed record OpenDocument(IntPtr Handle, GCHandle Pin, PdfDocumentInfo Info);
}
