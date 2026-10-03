using System.Runtime.InteropServices;
using Avalonia;
using Avalonia.Media.Imaging;
using Avalonia.Platform;
using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.Models;
using CleanCutPDF.Core.Pdf;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace CleanCutPDF.App.ViewModels;

/// <summary>
/// The zoom window (1.x fullscreen preview): opens at fit-to-width, Ctrl+scroll
/// or the buttons zoom from 50% to 500%. The current image is stretched
/// immediately and a sharp render replaces it in the background.
/// </summary>
public sealed partial class ZoomViewModel(IPdfEngine engine, AppLog log, string path, string fileName, int pageCount, int pageIndex)
    : ObservableObject
{
    public const double MinScale = 0.5;
    public const double MaxScale = 5.0;

    private CancellationTokenSource? _renderCts;
    private float _pageWidthPoints = 612, _pageHeightPoints = 792;
    private double _renderScaling = 1;

    public string Title => $"{fileName} — page {PageIndex + 1} of {pageCount}";

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(Title))]
    [NotifyCanExecuteChangedFor(nameof(PreviousPageCommand), nameof(NextPageCommand))]
    public partial int PageIndex { get; private set; } = pageIndex;

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(DisplayWidth), nameof(DisplayHeight), nameof(ZoomText))]
    public partial double Scale { get; private set; } = 1;

    [ObservableProperty]
    public partial Bitmap? PageImage { get; private set; }

    [ObservableProperty]
    public partial bool IsLoading { get; private set; }

    [ObservableProperty]
    public partial string? ErrorMessage { get; private set; }

    public double DisplayWidth => _pageWidthPoints * Scale;
    public double DisplayHeight => _pageHeightPoints * Scale;
    public string ZoomText => $"{Scale:P0}";

    /// <summary>Called once the window knows its size: zoom to fit the width (between 100% and 500%, like 1.x).</summary>
    public async Task InitializeAsync(double viewportWidth, double renderScaling)
    {
        _renderScaling = renderScaling;
        await LoadPageSizeAsync();
        Scale = Math.Clamp(Math.Round((viewportWidth - 40) / _pageWidthPoints, 2), 1.0, MaxScale);
        await RenderAsync();
    }

    // Synchronous on purpose: every click counts immediately, even while the
    // sharper render from the previous click is still on its way.
    [RelayCommand]
    private void ZoomIn() => _ = SetScaleAsync(Scale + 0.25);

    [RelayCommand]
    private void ZoomOut() => _ = SetScaleAsync(Scale - 0.25);

    [RelayCommand]
    private void ActualSize() => _ = SetScaleAsync(1.0);

    public Task SetScaleAsync(double scale)
    {
        var clamped = Math.Clamp(Math.Round(scale, 2), MinScale, MaxScale);
        if (Math.Abs(clamped - Scale) < 0.001)
        {
            return Task.CompletedTask;
        }

        Scale = clamped; // The old image stretches at once; the sharp one follows.
        return RenderAsync(debounce: true);
    }

    [RelayCommand(CanExecute = nameof(CanGoPrevious))]
    private async Task PreviousPageAsync()
    {
        PageIndex--;
        await LoadPageSizeAsync();
        await RenderAsync();
    }

    private bool CanGoPrevious() => PageIndex > 0;

    [RelayCommand(CanExecute = nameof(CanGoNext))]
    private async Task NextPageAsync()
    {
        PageIndex++;
        await LoadPageSizeAsync();
        await RenderAsync();
    }

    private bool CanGoNext() => PageIndex < pageCount - 1;

    private async Task LoadPageSizeAsync()
    {
        try
        {
            var page = await engine.AnalyzePageAsync(path, PageIndex, PdfWorkPriority.High);
            _pageWidthPoints = Math.Max(1, page.WidthPoints);
            _pageHeightPoints = Math.Max(1, page.HeightPoints);
            OnPropertyChanged(nameof(DisplayWidth));
            OnPropertyChanged(nameof(DisplayHeight));
        }
        catch (Exception error)
        {
            ErrorMessage = error is PdfOpenException ? error.Message : "This page could not be loaded.";
            log.Warning("Zoom", $"{fileName} page {PageIndex + 1}: {error.Message}");
        }
    }

    private async Task RenderAsync(bool debounce = false)
    {
        _renderCts?.Cancel();
        var cts = _renderCts = new CancellationTokenSource();
        var token = cts.Token;
        IsLoading = true;
        try
        {
            if (debounce)
            {
                await Task.Delay(150, token);
            }

            var width = (int)Math.Round(_pageWidthPoints * Scale * _renderScaling);
            var page = await engine.RenderPageAsync(path, PageIndex, width, PdfWorkPriority.High, token);
            var bitmap = await Task.Run(() => ToBitmap(page), token);
            var old = PageImage;
            PageImage = bitmap;
            old?.Dispose();
            ErrorMessage = null;
        }
        catch (OperationCanceledException)
        {
        }
        catch (Exception error)
        {
            ErrorMessage = error is PdfOpenException ? error.Message : "This page could not be shown at this size.";
            log.Warning("Zoom", $"{fileName} page {PageIndex + 1} at {Scale:P0}: {error.Message}");
        }
        finally
        {
            if (ReferenceEquals(_renderCts, cts))
            {
                IsLoading = false;
            }
        }
    }

    public void Close()
    {
        _renderCts?.Cancel();
        PageImage?.Dispose();
        PageImage = null;
    }

    private static Bitmap ToBitmap(RenderedPage page)
    {
        var pin = GCHandle.Alloc(page.Pixels, GCHandleType.Pinned);
        try
        {
            return new Bitmap(PixelFormat.Bgra8888, AlphaFormat.Premul, pin.AddrOfPinnedObject(),
                new PixelSize(page.Width, page.Height), new Vector(96, 96), page.Stride);
        }
        finally
        {
            pin.Free();
        }
    }
}
