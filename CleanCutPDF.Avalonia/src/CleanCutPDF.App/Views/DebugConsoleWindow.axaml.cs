using Avalonia.Controls;
using Avalonia.Input.Platform;
using Avalonia.Interactivity;
using CleanCutPDF.App.ViewModels;

namespace CleanCutPDF.App.Views;

public partial class DebugConsoleWindow : Window
{
    public DebugConsoleWindow()
    {
        InitializeComponent();
        DataContextChanged += (_, _) =>
        {
            if (DataContext is DebugConsoleViewModel vm)
            {
                vm.EntriesAppended += (_, _) =>
                {
                    if (vm.AutoScroll && vm.Entries.Count > 0)
                    {
                        EntryList.ScrollIntoView(vm.Entries.Count - 1);
                    }
                };
            }
        };
        Closed += (_, _) => (DataContext as DebugConsoleViewModel)?.Dispose();
    }

    private async void OnCopyAll(object? sender, RoutedEventArgs e)
    {
        if (DataContext is DebugConsoleViewModel vm && Clipboard is { } clipboard)
        {
            await clipboard.SetTextAsync(vm.AllText());
        }
    }
}
