using System.Runtime.InteropServices;

namespace CleanCutPDF.Core.Pdf.Native;

/// <summary>
/// Minimal P/Invoke surface for PDFium (https://pdfium.googlesource.com/pdfium/).
/// The native binaries come from the bblanchon.PDFium.* NuGet packages
/// (pdfium.dll on Windows, libpdfium.dylib on macOS).
///
/// PDFium is NOT thread-safe. Every call must be made from
/// <see cref="PdfWorkerThread"/>; never call these directly from UI code.
/// </summary>
internal static unsafe class PdfiumNative
{
    private const string Library = "pdfium";

    public const int FPDF_ANNOT = 0x01;
    public const int FPDF_LCD_TEXT = 0x02;
    public const int FPDF_GRAYSCALE = 0x08;

    // FPDF_GetLastError codes
    public const uint FPDF_ERR_SUCCESS = 0;
    public const uint FPDF_ERR_UNKNOWN = 1;
    public const uint FPDF_ERR_FILE = 2;
    public const uint FPDF_ERR_FORMAT = 3;
    public const uint FPDF_ERR_PASSWORD = 4;
    public const uint FPDF_ERR_SECURITY = 5;
    public const uint FPDF_ERR_PAGE = 6;

    [DllImport(Library)]
    public static extern void FPDF_InitLibrary();

    [DllImport(Library)]
    public static extern void FPDF_DestroyLibrary();

    // `unsigned long` is 32-bit on Windows and 64-bit on macOS; CULong handles both.
    [DllImport(Library)]
    public static extern CULong FPDF_GetLastError();

    [DllImport(Library, CharSet = CharSet.Ansi, BestFitMapping = false)]
    public static extern IntPtr FPDF_LoadMemDocument64(IntPtr data, nuint size, string? password);

    [DllImport(Library)]
    public static extern void FPDF_CloseDocument(IntPtr document);

    [DllImport(Library)]
    public static extern int FPDF_GetPageCount(IntPtr document);

    [DllImport(Library)]
    public static extern IntPtr FPDF_LoadPage(IntPtr document, int pageIndex);

    [DllImport(Library)]
    public static extern void FPDF_ClosePage(IntPtr page);

    [DllImport(Library)]
    public static extern float FPDF_GetPageWidthF(IntPtr page);

    [DllImport(Library)]
    public static extern float FPDF_GetPageHeightF(IntPtr page);

    [DllImport(Library)]
    public static extern IntPtr FPDFBitmap_Create(int width, int height, int alpha);

    [DllImport(Library)]
    public static extern int FPDFBitmap_FillRect(IntPtr bitmap, int left, int top, int width, int height, CULong color);

    [DllImport(Library)]
    public static extern IntPtr FPDFBitmap_GetBuffer(IntPtr bitmap);

    [DllImport(Library)]
    public static extern int FPDFBitmap_GetStride(IntPtr bitmap);

    [DllImport(Library)]
    public static extern void FPDFBitmap_Destroy(IntPtr bitmap);

    [DllImport(Library)]
    public static extern void FPDF_RenderPageBitmap(
        IntPtr bitmap, IntPtr page, int startX, int startY, int sizeX, int sizeY, int rotate, int flags);

    [DllImport(Library)]
    public static extern int FPDFPage_GetAnnotCount(IntPtr page);

    [DllImport(Library)]
    public static extern IntPtr FPDF_CreateNewDocument();

    [DllImport(Library)]
    public static extern int FPDF_ImportPagesByIndex(IntPtr destDocument, IntPtr sourceDocument, int* pageIndices,
        CULong length, int insertIndex);

    [DllImport(Library)]
    public static extern int FPDF_SaveAsCopy(IntPtr document, FileWrite* fileWrite, CULong flags);

    /// <summary>FPDF_FILEWRITE plus a trailing GCHandle so the callback can find its stream.</summary>
    [StructLayout(LayoutKind.Sequential)]
    public struct FileWrite
    {
        public int Version;
        public delegate* unmanaged[Cdecl]<FileWrite*, void*, CULong, int> WriteBlock;
        public IntPtr StreamHandle;
    }

    [DllImport(Library)]
    public static extern IntPtr FPDFText_LoadPage(IntPtr page);

    [DllImport(Library)]
    public static extern void FPDFText_ClosePage(IntPtr textPage);

    [DllImport(Library)]
    public static extern int FPDFText_CountChars(IntPtr textPage);

    [DllImport(Library)]
    public static extern int FPDFText_GetText(IntPtr textPage, int startIndex, int count, ushort* result);
}
