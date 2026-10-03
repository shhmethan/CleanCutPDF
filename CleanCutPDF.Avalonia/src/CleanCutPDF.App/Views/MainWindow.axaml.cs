using Avalonia.Controls;
using Avalonia.Controls.Primitives;
using Avalonia.Input;
using Avalonia.Platform.Storage;
using Avalonia.Threading;
using Avalonia.VisualTree;
using CleanCutPDF.App.Services;
using CleanCutPDF.App.ViewModels;

namespace CleanCutPDF.App.Views;

public partial class MainWindow : Window
{
    public MainWindow() : this([])
    {
    }

    public MainWindow(IReadOnlyList<string> startupFiles)
    {
        InitializeComponent();
        AddHandler(DragDrop.DragOverEvent, OnDragOver);
        // Ctrl+Alt+D opens the debug console from anywhere (1.x shortcut).
        AddHandler(KeyDownEvent, (_, e) =>
        {
            if (DataContext is not MainWindowViewModel vm)
            {
                return;
            }

            if (e.Key == Key.D && e.KeyModifiers.HasFlag(KeyModifiers.Control) && e.KeyModifiers.HasFlag(KeyModifiers.Alt))
            {
                vm.OpenDebugConsole();
                e.Handled = true;
            }
            else if (KeyGestureText.From(e) is { } gesture && vm.MatchShortcut(gesture) is { } action)
            {
                // The user's keyboard shortcuts (Settings › Keyboard shortcuts).
                e.Handled = true;
                _ = vm.RunShortcutAsync(action);
            }
        }, Avalonia.Interactivity.RoutingStrategies.Tunnel);
        AddHandler(DragDrop.DropEvent, OnDrop);
        Opened += async (_, _) =>
        {
            if (DataContext is MainWindowViewModel vm)
            {
                vm.FocusRequested += (_, name) => Dispatcher.UIThread.Post(() => FocusNamed(name), DispatcherPriority.Background);
                vm.PasteRequested += (_, _) =>
                {
                    // 1.x "Paste Clipboard": into whichever text box has the cursor.
                    if (FocusManager?.GetFocusedElement() is TextBox { IsReadOnly: false } box)
                    {
                        box.Paste();
                    }
                };
                await vm.InitializeAsync(startupFiles);
            }
        };
    }

    /// <summary>Focuses the named control, or the first input inside it (posted so a page change has finished).</summary>
    private void FocusNamed(string name)
    {
        var target = this.GetVisualDescendants().OfType<Control>().FirstOrDefault(c => c.Name == name);
        if (target is null or TextBox)
        {
            target?.Focus(NavigationMethod.Tab);
            return;
        }

        var inputs = target.GetVisualDescendants().OfType<Control>()
            .Where(c => c is { Focusable: true, IsEffectivelyVisible: true, IsEffectivelyEnabled: true }).ToList();
        (inputs.FirstOrDefault(c => c is TextBox)
         ?? inputs.FirstOrDefault(c => c is ComboBox or ToggleButton)
         ?? target).Focus(NavigationMethod.Tab);
    }

    private static void OnDragOver(object? sender, DragEventArgs e)
    {
        e.DragEffects = e.DataTransfer.TryGetFiles() is { Length: > 0 }
            ? DragDropEffects.Copy
            : DragDropEffects.None;
    }

    private async void OnDrop(object? sender, DragEventArgs e)
    {
        if (DataContext is not MainWindowViewModel vm || e.DataTransfer.TryGetFiles() is not { } items)
        {
            return;
        }

        var paths = items.Select(item => item.TryGetLocalPath()).OfType<string>().ToList();
        if (paths.Count > 0)
        {
            await vm.ImportDroppedFilesAsync(paths);
        }
    }
}
