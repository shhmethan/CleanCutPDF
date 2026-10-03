using System.Runtime.InteropServices;
using Avalonia;
using Avalonia.Media.Imaging;
using Avalonia.Platform;
using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Models;
using CleanCutPDF.Core.Pdf;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace CleanCutPDF.App.ViewModels;

/// <summary>
/// Page preview with navigation. Every render runs off the UI thread; starting
/// a new render cancels the previous one, the previous page stays visible
/// until the new one is ready (no flicker), and neighbours are prefetched.
/// </summary>
public sealed partial class PdfPreviewViewModel(PagePreviewService previews, CrashLog crashLog, AppLog log,
    Action<IPreviewDocument, int>? openZoom = null) : ObservableObject
{
    /// <summary>Opens the current page in the zoom window.</summary>
    [RelayCommand]
    private void Zoom()
    {
        if (_document is not null)
        {
            openZoom?.Invoke(_document, PageIndex);
        }
    }

    private static readonly TimeSpan ResizeDebounce = TimeSpan.FromMilliseconds(150);

    private CancellationTokenSource? _renderCts;
    private CancellationTokenSource? _resizeCts;
    private IPreviewDocument? _document;
    private int _renderWidth = PagePreviewService.BucketWidth(800);

    [ObservableProperty]
    public partial Bitmap? PageImage { get; private set; }

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(PageLabel))]
    [NotifyCanExecuteChangedFor(nameof(PreviousPageCommand), nameof(NextPageCommand))]
    public partial int PageIndex { get; private set; }

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(PageLabel))]
    [NotifyCanExecuteChangedFor(nameof(PreviousPageCommand), nameof(NextPageCommand))]
    public partial int PageCount { get; private set; }

    [ObservableProperty]
    public partial bool IsLoading { get; private set; }

    [ObservableProperty]
    public partial string? ErrorMessage { get; private set; }

    [ObservableProperty]
    public partial string PageInput { get; set; } = "1";

    [ObservableProperty]
    public partial bool HasDocument { get; private set; }

    public string PageLabel => PageCount > 0 ? $"Page {PageIndex + 1} of {PageCount}" : string.Empty;

    public void ShowDocument(IPreviewDocument? document)
    {
        if (ReferenceEquals(_document, document))
        {
            return;
        }

        _renderCts?.Cancel();
        _document = document;
        HasDocument = document is not null;
        ErrorMessage = null;
        PageIndex = 0;
        PageInput = "1";
        PageCount = document?.PageCount ?? 0;
        ReplaceImage(null);

        if (document is not null)
        {
            _ = RenderAsync();
        }
    }

    /// <summary>Called by the view when the available width changes.</summary>
    public void UpdateViewportWidth(double pixels)
    {
        var bucket = PagePreviewService.BucketWidth(pixels);
        if (bucket == _renderWidth)
        {
            return;
        }

        _renderWidth = bucket;
        _resizeCts?.Cancel();
        var cts = _resizeCts = new CancellationTokenSource();
        _ = RerenderAfterResizeAsync(cts.Token);
    }

    [RelayCommand(CanExecute = nameof(CanGoPrevious))]
    private void PreviousPage() => ShowPage(PageIndex - 1);

    private bool CanGoPrevious() => PageIndex > 0;

    [RelayCommand(CanExecute = nameof(CanGoNext))]
    private void NextPage() => ShowPage(PageIndex + 1);

    private bool CanGoNext() => PageIndex < PageCount - 1;

    [RelayCommand]
    private void GoToPage()
    {
        if (PageCount <= 0)
        {
            return;
        }

        if (!int.TryParse(PageInput?.Trim(), out var number) || number < 1 || number > PageCount)
        {
            ErrorMessage = $"Enter a page number from 1 to {PageCount}.";
            return;
        }

        ShowPage(number - 1);
    }

    public void ShowPage(int pageIndex)
    {
        if (_document is null)
        {
            return;
        }

        var max = Math.Max(0, PageCount - 1);
        PageIndex = Math.Clamp(pageIndex, 0, max);
        PageInput = (PageIndex + 1).ToString();
        _ = RenderAsync();
    }

    private async Task RerenderAfterResizeAsync(CancellationToken token)
    {
        try
        {
            await Task.Delay(ResizeDebounce, token);
            if (_document is not null)
            {
                await RenderAsync();
            }
        }
        catch (OperationCanceledException)
        {
        }
    }

    private async Task RenderAsync()
    {
        var document = _document;
        if (document is null)
        {
            return;
        }

        _renderCts?.Cancel();
        var cts = _renderCts = new CancellationTokenSource();
        var token = cts.Token;
        var pageIndex = PageIndex;
        var width = _renderWidth;

        IsLoading = true;
        ErrorMessage = null;
        try
        {
            var started = System.Diagnostics.Stopwatch.GetTimestamp();
            var page = await previews.GetPageAsync(document.FilePath, pageIndex, width, token);
            log.Debug("Preview", $"{document.FileName} page {pageIndex + 1} at {width}px ready in " +
                                 $"{System.Diagnostics.Stopwatch.GetElapsedTime(started).TotalMilliseconds:N0} ms");
            var bitmap = await Task.Run(() => ToBitmap(page), token);
            if (token.IsCancellationRequested || !ReferenceEquals(document, _document))
            {
                bitmap.Dispose();
                return;
            }

            PageCount = page.PageCount;
            ReplaceImage(bitmap);
            previews.Prefetch(document.FilePath, pageIndex, page.PageCount, width, token);
        }
        catch (OperationCanceledException)
        {
            // A newer request replaced this one.
        }
        catch (PdfOpenException error)
        {
            log.Warning("Preview", $"{document.FileName} page {pageIndex + 1}: {error.Message}");
            ErrorMessage = error.Message;
        }
        catch (Exception error)
        {
            crashLog.Write($"Preview of {document.FilePath} page {pageIndex + 1} failed", error);
            ErrorMessage = "This page could not be previewed. Details were saved to crash.log.";
        }
        finally
        {
            if (ReferenceEquals(_renderCts, cts))
            {
                IsLoading = false;
            }
        }
    }

    private void ReplaceImage(Bitmap? bitmap)
    {
        var old = PageImage;
        PageImage = bitmap;
        old?.Dispose();
    }

    private static Bitmap ToBitmap(RenderedPage page)
    {
        var pin = GCHandle.Alloc(page.Pixels, GCHandleType.Pinned);
        try
        {
            // The constructor copies the pixels, so the managed buffer can stay in the cache.
            return new Bitmap(
                PixelFormat.Bgra8888,
                AlphaFormat.Premul,
                pin.AddrOfPinnedObject(),
                new PixelSize(page.Width, page.Height),
                new Vector(96, 96),
                page.Stride);
        }
        finally
        {
            pin.Free();
        }
    }
}

/// <summary>Anything the preview can show: an Inbox document or a Rename Only file.</summary>
public interface IPreviewDocument
{
    string FilePath { get; }
    string FileName { get; }
    int PageCount { get; }
}
