using Avalonia;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using CleanCutPDF.App.ViewModels;

namespace CleanCutPDF.App.Views;

public partial class ZoomWindow : Window
{
    public ZoomWindow()
    {
        InitializeComponent();

        // Tunnel so Ctrl+scroll zooms before the ScrollViewer scrolls.
        Scroller.AddHandler(PointerWheelChangedEvent, OnWheel, RoutingStrategies.Tunnel);
        // Tunnel so Esc and Ctrl+/-/0 work whichever control has focus.
        AddHandler(KeyDownEvent, OnKeyDown, RoutingStrategies.Tunnel);
        Opened += async (_, _) =>
        {
            if (DataContext is ZoomViewModel vm)
            {
                await vm.InitializeAsync(Scroller.Bounds.Width > 0 ? Scroller.Bounds.Width : Bounds.Width, RenderScaling);
            }
        };
        Closed += (_, _) => (DataContext as ZoomViewModel)?.Close();
    }

    private ZoomViewModel? ViewModel => DataContext as ZoomViewModel;

    private async void OnWheel(object? sender, PointerWheelEventArgs e)
    {
        if (ViewModel is not { } vm)
        {
            return;
        }

        if (e.KeyModifiers.HasFlag(KeyModifiers.Control))
        {
            e.Handled = true;
            await vm.SetScaleAsync(vm.Scale + (e.Delta.Y > 0 ? 0.25 : -0.25));
        }
        else if (e.KeyModifiers.HasFlag(KeyModifiers.Shift))
        {
            e.Handled = true;
            Scroller.Offset = new Vector(Scroller.Offset.X - e.Delta.Y * 60, Scroller.Offset.Y);
        }
    }

    private async void OnKeyDown(object? sender, KeyEventArgs e)
    {
        if (ViewModel is not { } vm)
        {
            return;
        }

        switch (e.Key)
        {
            case Key.Escape:
                Close();
                break;
            case Key.OemPlus or Key.Add when e.KeyModifiers.HasFlag(KeyModifiers.Control):
                await vm.SetScaleAsync(vm.Scale + 0.25);
                break;
            case Key.OemMinus or Key.Subtract when e.KeyModifiers.HasFlag(KeyModifiers.Control):
                await vm.SetScaleAsync(vm.Scale - 0.25);
                break;
            case Key.D0 or Key.NumPad0 when e.KeyModifiers.HasFlag(KeyModifiers.Control):
                await vm.SetScaleAsync(1.0);
                break;
            default:
                return;
        }

        e.Handled = true;
    }
}
