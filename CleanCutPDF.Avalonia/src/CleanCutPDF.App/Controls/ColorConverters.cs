using System.Globalization;
using Avalonia;
using Avalonia.Data.Converters;
using Avalonia.Media;

namespace CleanCutPDF.App.Controls;

/// <summary>"#RRGGBB" → brush; blank keeps the control's normal style.</summary>
public sealed class HexToBrushConverter : IValueConverter
{
    public static readonly HexToBrushConverter Background = new(contrast: false);

    /// <summary>Black or white text, whichever reads better on the color (1.x rule).</summary>
    public static readonly HexToBrushConverter Foreground = new(contrast: true);

    private readonly bool _contrast;

    private HexToBrushConverter(bool contrast) => _contrast = contrast;

    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is not string text || !Color.TryParse(text, out var color))
        {
            return AvaloniaProperty.UnsetValue;
        }

        if (!_contrast)
        {
            return new SolidColorBrush(color);
        }

        return color.R * 299 + color.G * 587 + color.B * 114 > 150_000 ? Brushes.Black : Brushes.White;
    }

    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture) =>
        throw new NotSupportedException();
}
