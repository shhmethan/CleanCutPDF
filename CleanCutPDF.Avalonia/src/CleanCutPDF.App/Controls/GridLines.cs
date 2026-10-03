using Avalonia;
using Avalonia.Controls;
using Avalonia.Media;

namespace CleanCutPDF.App.Controls;

/// <summary>The square guide grid behind the Layout Designer's tiles.</summary>
public sealed class GridLines : Control
{
    public static readonly StyledProperty<int> GridSizeProperty =
        AvaloniaProperty.Register<GridLines, int>(nameof(GridSize), 24);

    public static readonly StyledProperty<IBrush?> StrokeProperty =
        AvaloniaProperty.Register<GridLines, IBrush?>(nameof(Stroke));

    static GridLines() => AffectsRender<GridLines>(GridSizeProperty, StrokeProperty);

    public int GridSize
    {
        get => GetValue(GridSizeProperty);
        set => SetValue(GridSizeProperty, value);
    }

    public IBrush? Stroke
    {
        get => GetValue(StrokeProperty);
        set => SetValue(StrokeProperty, value);
    }

    public override void Render(DrawingContext context)
    {
        if (Stroke is null || GridSize < 2)
        {
            return;
        }

        var pen = new Pen(Stroke, 1);
        for (double x = 0; x <= Bounds.Width; x += GridSize)
        {
            context.DrawLine(pen, new Point(x + 0.5, 0), new Point(x + 0.5, Bounds.Height));
        }

        for (double y = 0; y <= Bounds.Height; y += GridSize)
        {
            context.DrawLine(pen, new Point(0, y + 0.5), new Point(Bounds.Width, y + 0.5));
        }
    }
}
