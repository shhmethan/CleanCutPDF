using Avalonia.Controls;
using Avalonia.Input;
using CleanCutPDF.App.ViewModels.Editor;

namespace CleanCutPDF.App.Controls;

/// <summary>A TextBox for workspace fields: currency values tidy themselves when the user leaves the box.</summary>
public sealed class FieldTextBox : TextBox
{
    protected override Type StyleKeyOverride => typeof(TextBox);

    protected override void OnLostFocus(FocusChangedEventArgs e)
    {
        base.OnLostFocus(e);
        (DataContext as TextFieldViewModel)?.Normalize();
    }
}
