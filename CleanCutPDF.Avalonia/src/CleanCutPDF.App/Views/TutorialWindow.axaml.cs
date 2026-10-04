using Avalonia.Controls;
using CleanCutPDF.App.ViewModels;

namespace CleanCutPDF.App.Views;

public partial class TutorialWindow : Window
{
    private bool _closing;

    public TutorialWindow()
    {
        InitializeComponent();

        DataContextChanged += (_, _) =>
        {
            if (DataContext is TutorialViewModel vm)
            {
                vm.CloseRequested += OnCloseRequested;
            }
        };

        // Closing with the X counts as having seen the tour.
        Closing += (_, _) =>
        {
            if (!_closing && DataContext is TutorialViewModel vm)
            {
                _closing = true;
                vm.Finish();
            }
        };
        Closed += (_, _) =>
        {
            if (DataContext is TutorialViewModel vm)
            {
                vm.CloseRequested -= OnCloseRequested; // The view-model outlives this window.
            }
        };
    }

    private void OnCloseRequested(object? sender, EventArgs e)
    {
        if (!_closing)
        {
            _closing = true;
            Close();
        }
    }
}
