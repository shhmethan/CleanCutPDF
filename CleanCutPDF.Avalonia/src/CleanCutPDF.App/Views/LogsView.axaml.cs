using Avalonia.Controls;
using CleanCutPDF.App.ViewModels;

namespace CleanCutPDF.App.Views;

public partial class LogsView : UserControl
{
    public LogsView()
    {
        InitializeComponent();

        // The history is read the first time the page is shown, not at startup.
        AttachedToVisualTree += async (_, _) =>
        {
            if (DataContext is LogsViewModel vm)
            {
                await vm.EnsureLoadedAsync();
            }
        };
    }
}
