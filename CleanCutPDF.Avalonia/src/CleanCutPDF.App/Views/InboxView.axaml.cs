using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.VisualTree;
using CleanCutPDF.App.ViewModels;

namespace CleanCutPDF.App.Views;

public partial class InboxView : UserControl
{
    public InboxView()
    {
        InitializeComponent();
        DocumentList.DoubleTapped += OnDocumentDoubleTapped;
        // Tunnel so the ListBox's own key handling cannot swallow Enter first.
        DocumentList.AddHandler(KeyDownEvent, OnDocumentListKeyDown, RoutingStrategies.Tunnel);
    }

    /// <summary>Enter opens the focused PDF (keyboard equivalent of double-click).</summary>
    private void OnDocumentListKeyDown(object? sender, KeyEventArgs e)
    {
        if (e.Key == Key.Enter
            && DocumentList.SelectedItem is DocumentItemViewModel document
            && DataContext is InboxViewModel vm)
        {
            vm.OpenInEditorCommand.Execute(document);
            e.Handled = true;
        }
    }

    /// <summary>A PDF opens only on an explicit double-click (matches the 1.10.1 behavior).</summary>
    private void OnDocumentDoubleTapped(object? sender, TappedEventArgs e)
    {
        var item = (e.Source as Control)?.FindAncestorOfType<ListBoxItem>(includeSelf: true);
        if (item?.DataContext is DocumentItemViewModel document && DataContext is InboxViewModel vm)
        {
            vm.OpenInEditorCommand.Execute(document);
        }
    }
}

