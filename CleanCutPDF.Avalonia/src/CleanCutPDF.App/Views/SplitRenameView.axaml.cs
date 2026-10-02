using Avalonia.Controls;
using CleanCutPDF.App.ViewModels;

namespace CleanCutPDF.App.Views;

public partial class SplitRenameView : UserControl
{
    public SplitRenameView()
    {
        InitializeComponent();

        // Render at the real pixel width of the preview area (bucketed and
        // debounced in the view-model) instead of a fixed 2x oversample.
        PreviewViewport.SizeChanged += (_, e) =>
        {
            if (DataContext is SplitRenameViewModel vm && e.NewSize.Width > 0)
            {
                var scaling = TopLevel.GetTopLevel(this)?.RenderScaling ?? 1.0;
                vm.Preview.UpdateViewportWidth((e.NewSize.Width - 24) * scaling);
            }
        };
    }
}
