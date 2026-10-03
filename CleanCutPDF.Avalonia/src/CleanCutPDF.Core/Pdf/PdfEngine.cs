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

    /// <summary>Text, annotation count, and size of a page, in one call.</summary>
    Task<PageAnalysis> AnalyzePageAsync(string path, int pageIndex, PdfWorkPriority priority,
        CancellationToken cancellationToken = default);

    /// <summary>Renders a page into exactly width × height pixels (used by the visual checks).</summary>
    Task<RenderedPage> RenderPageSizedAsync(string path, int pageIndex, int width, int height, bool grayscale,
        PdfWorkPriority priority, CancellationToken cancellationToken = default);

    /// <summary>Copies the given pages (0-based, in order) into a new PDF and returns its bytes.</summary>
    Task<byte[]> ExtractPagesAsync(string path, IReadOnlyList<int> pageIndices, CancellationToken cancellationToken = default);

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

    public Task<RenderedPage> RenderPageAsync(string path, int pageIndex, int targetWidth,
        PdfWorkPriority priority = PdfWorkPriority.High, CancellationToken cancellationToken = default) =>
        WithDocumentAsync(path, document =>
        {
            cancellationToken.ThrowIfCancellationRequested();
            return RenderOnWorker(document, pageIndex, (pageWidth, pageHeight) =>
            {
                var width = Math.Clamp(targetWidth, 16, MaxRenderDimension);
                var height = Math.Clamp((int)Math.Round(width * pageHeight / pageWidth), 16, MaxRenderDimension);
                return (width, height);
            }, PdfiumNative.FPDF_ANNOT);
        }, priority, cancellationToken);

    public Task<RenderedPage> RenderPageSizedAsync(string path, int pageIndex, int width, int height, bool grayscale,
        PdfWorkPriority priority, CancellationToken cancellationToken = default) =>
        WithDocumentAsync(path, document =>
        {
            cancellationToken.ThrowIfCancellationRequested();
            return RenderOnWorker(document, pageIndex,
                (_, _) => (Math.Clamp(width, 1, MaxRenderDimension), Math.Clamp(height, 1, MaxRenderDimension)),
                PdfiumNative.FPDF_ANNOT | (grayscale ? PdfiumNative.FPDF_GRAYSCALE : 0));
        }, priority, cancellationToken);

    public Task<string> ExtractPageTextAsync(string path, int pageIndex, CancellationToken cancellationToken = default) =>
        WithDocumentAsync(path, document => WithPage(document, pageIndex, ReadText), PdfWorkPriority.High, cancellationToken);

    public Task<PageAnalysis> AnalyzePageAsync(string path, int pageIndex, PdfWorkPriority priority,
        CancellationToken cancellationToken = default) =>
        WithDocumentAsync(path, document => WithPage(document, pageIndex, page => new PageAnalysis(
            pageIndex,
            ReadText(page),
            PdfiumNative.FPDFPage_GetAnnotCount(page),
            PdfiumNative.FPDF_GetPageWidthF(page),
            PdfiumNative.FPDF_GetPageHeightF(page))), priority, cancellationToken);

    public Task<byte[]> ExtractPagesAsync(string path, IReadOnlyList<int> pageIndices,
        CancellationToken cancellationToken = default) =>
        WithDocumentAsync(path, document => CopyPagesOnWorker(document, pageIndices), PdfWorkPriority.High,
            cancellationToken);

    /// <summary>
    /// Runs work against an open document on the PDF thread. A document can be
    /// evicted from the LRU between Open and the work when many files are busy;
    /// it is reopened once in that case.
    /// </summary>
    private async Task<T> WithDocumentAsync<T>(string path, Func<OpenDocument, T> work, PdfWorkPriority priority,
        CancellationToken cancellationToken)
    {
        for (var attempt = 0; ; attempt++)
        {
            var info = await OpenAsync(path, cancellationToken);
            try
            {
                return await _worker.InvokeAsync(() => work(Get(info.Path)), priority, cancellationToken);
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

    private static T WithPage<T>(OpenDocument document, int pageIndex, Func<IntPtr, T> work)
    {
        if (pageIndex < 0 || pageIndex >= document.Info.PageCount)
        {
            throw new ArgumentOutOfRangeException(nameof(pageIndex), $"Page {pageIndex + 1} does not exist.");
        }

        var page = PdfiumNative.FPDF_LoadPage(document.Handle, pageIndex);
        if (page == IntPtr.Zero)
        {
            throw new PdfOpenException($"Page {pageIndex + 1} could not be loaded.");
        }

        try
        {
            return work(page);
        }
        finally
        {
            PdfiumNative.FPDF_ClosePage(page);
        }
    }

    private static RenderedPage RenderOnWorker(OpenDocument document, int pageIndex,
        Func<float, float, (int Width, int Height)> size, int flags) =>
        WithPage(document, pageIndex, page =>
        {
            var pageWidth = Math.Max(1f, PdfiumNative.FPDF_GetPageWidthF(page));
            var pageHeight = Math.Max(1f, PdfiumNative.FPDF_GetPageHeightF(page));
            var (width, height) = size(pageWidth, pageHeight);

            var bitmap = PdfiumNative.FPDFBitmap_Create(width, height, 1);
            if (bitmap == IntPtr.Zero)
            {
                throw new PdfOpenException("Not enough memory to render this page.");
            }

            try
            {
                PdfiumNative.FPDFBitmap_FillRect(bitmap, 0, 0, width, height, new CULong(0xFFFFFFFF));
                PdfiumNative.FPDF_RenderPageBitmap(bitmap, page, 0, 0, width, height, 0, flags);

                var stride = PdfiumNative.FPDFBitmap_GetStride(bitmap);
                var pixels = new byte[stride * height];
                Marshal.Copy(PdfiumNative.FPDFBitmap_GetBuffer(bitmap), pixels, 0, pixels.Length);
                return new RenderedPage(pageIndex, document.Info.PageCount, width, height, stride, pixels);
            }
            finally
            {
                PdfiumNative.FPDFBitmap_Destroy(bitmap);
            }
        });

    private static unsafe string ReadText(IntPtr page)
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

    private static unsafe byte[] CopyPagesOnWorker(OpenDocument source, IReadOnlyList<int> pageIndices)
    {
        if (pageIndices.Count == 0)
        {
            throw new ArgumentException("At least one page is required.", nameof(pageIndices));
        }

        if (pageIndices.Any(i => i < 0 || i >= source.Info.PageCount))
        {
            throw new ArgumentOutOfRangeException(nameof(pageIndices), "A page number is outside the document.");
        }

        var destination = PdfiumNative.FPDF_CreateNewDocument();
        if (destination == IntPtr.Zero)
        {
            throw new PdfOpenException("A new PDF could not be created.");
        }

        var output = new MemoryStream();
        var handle = GCHandle.Alloc(output);
        try
        {
            var indices = pageIndices.ToArray();
            fixed (int* pointer = indices)
            {
                if (PdfiumNative.FPDF_ImportPagesByIndex(destination, source.Handle, pointer,
                        new CULong((uint)indices.Length), 0) == 0)
                {
                    throw new PdfOpenException($"Pages could not be copied from {Path.GetFileName(source.Info.Path)}.");
                }
            }

            var writer = new PdfiumNative.FileWrite
            {
                Version = 1,
                WriteBlock = &WriteBlock,
                StreamHandle = GCHandle.ToIntPtr(handle)
            };
            if (PdfiumNative.FPDF_SaveAsCopy(destination, &writer, new CULong(0)) == 0)
            {
                throw new PdfOpenException("The new PDF could not be saved.");
            }

            return output.ToArray();
        }
        finally
        {
            handle.Free();
            PdfiumNative.FPDF_CloseDocument(destination);
        }
    }

    [System.Runtime.InteropServices.UnmanagedCallersOnly(CallConvs = [typeof(System.Runtime.CompilerServices.CallConvCdecl)])]
    private static unsafe int WriteBlock(PdfiumNative.FileWrite* self, void* data, CULong size)
    {
        try
        {
            var stream = (MemoryStream)GCHandle.FromIntPtr(self->StreamHandle).Target!;
            stream.Write(new ReadOnlySpan<byte>(data, checked((int)size.Value)));
            return 1;
        }
        catch
        {
            return 0;
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
