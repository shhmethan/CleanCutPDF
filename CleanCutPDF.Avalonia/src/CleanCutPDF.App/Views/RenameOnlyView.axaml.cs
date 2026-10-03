using Avalonia.Controls;
using CleanCutPDF.App.ViewModels;

namespace CleanCutPDF.App.Views;

public partial class RenameOnlyView : UserControl
{
    public RenameOnlyView()
    {
        InitializeComponent();
        PreviewViewport.SizeChanged += (_, e) =>
        {
            if (DataContext is RenameOnlyViewModel vm && e.NewSize.Width > 0)
            {
                var scaling = TopLevel.GetTopLevel(this)?.RenderScaling ?? 1.0;
                vm.Preview.UpdateViewportWidth((e.NewSize.Width - 24) * scaling);
            }
        };
    }
}
