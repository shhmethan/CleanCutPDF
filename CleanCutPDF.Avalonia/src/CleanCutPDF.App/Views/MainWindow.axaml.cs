using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Platform.Storage;
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
        AddHandler(DragDrop.DropEvent, OnDrop);
        Opened += async (_, _) =>
        {
            if (DataContext is MainWindowViewModel vm)
            {
                await vm.InitializeAsync(startupFiles);
            }
        };
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
