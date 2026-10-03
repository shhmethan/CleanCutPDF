using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using CleanCutPDF.App.Services;
using CleanCutPDF.App.ViewModels;

namespace CleanCutPDF.App.Views;

public partial class SettingsView : UserControl
{
    public SettingsView()
    {
        InitializeComponent();

        // Press-to-capture for keyboard shortcuts: while a shortcut button is
        // waiting, the next key combination is recorded instead of acted on.
        AddHandler(KeyDownEvent, OnCaptureKeyDown, RoutingStrategies.Tunnel);
        AddHandler(LostFocusEvent, (_, e) =>
        {
            if (e.Source is Button { DataContext: KeybindRowViewModel { IsCapturing: true } })
            {
                (DataContext as SettingsViewModel)?.Keybinds.CancelCapture();
            }
        });
        DetachedFromVisualTree += (_, _) => (DataContext as SettingsViewModel)?.Keybinds.CancelCapture();
    }

    private void OnCaptureKeyDown(object? sender, KeyEventArgs e)
    {
        if (DataContext is not SettingsViewModel { Keybinds: { IsCapturing: true } keybinds })
        {
            return;
        }

        e.Handled = true;
        if (e.Key == Key.Escape)
        {
            keybinds.CancelCapture();
        }
        else if (KeyGestureText.From(e) is { } gesture)
        {
            keybinds.Capture(gesture);
        }
    }
}
