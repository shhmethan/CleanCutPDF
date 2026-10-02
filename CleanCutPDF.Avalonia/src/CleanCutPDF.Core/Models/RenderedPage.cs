namespace CleanCutPDF.Core.Models;

/// <summary>
/// A rendered page as raw premultiplied BGRA pixels. Core stays UI-agnostic;
/// the Avalonia layer converts this into a bitmap.
/// </summary>
public sealed class RenderedPage(int pageIndex, int pageCount, int width, int height, int stride, byte[] pixels)
{
    public int PageIndex { get; } = pageIndex;
    public int PageCount { get; } = pageCount;
    public int Width { get; } = width;
    public int Height { get; } = height;
    public int Stride { get; } = stride;
    public byte[] Pixels { get; } = pixels;

    public long ByteSize => Pixels.LongLength;
}
