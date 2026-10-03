using Avalonia;
using Avalonia.Controls;
using CleanCutPDF.App.ViewModels.Editor;
using CleanCutPDF.Core.Workspaces;

namespace CleanCutPDF.App.Controls;

/// <summary>
/// Lays out a Part's fields by their Layout Designer tiles. The placement
/// rules live in <see cref="FreeformLayout"/>; this panel only measures.
/// </summary>
public sealed class FreeformPanel : Panel
{
    private static readonly LayoutTile Fallback = new();

    protected override Size MeasureOverride(Size availableSize)
    {
        var width = double.IsInfinity(availableSize.Width) ? WorkspaceLayout.SurfaceWidth : availableSize.Width;
        var rects = Place(width, measure: true);
        return new Size(width, rects.Count == 0 ? 0 : rects.Max(r => r.Bottom));
    }

    protected override Size ArrangeOverride(Size finalSize)
    {
        var rects = Place(finalSize.Width, measure: false);
        for (var i = 0; i < Children.Count; i++)
        {
            Children[i].Arrange(new Rect(rects[i].X, rects[i].Y, rects[i].Width, rects[i].Height));
        }

        return new Size(finalSize.Width, Math.Max(finalSize.Height, rects.Count == 0 ? 0 : rects.Max(r => r.Bottom)));
    }

    private IReadOnlyList<LayoutRect> Place(double width, bool measure)
    {
        var tiles = Children.Select(c => (c.DataContext as FieldViewModel)?.Tile ?? Fallback).ToList();
        var heights = new double[tiles.Count];
        for (var i = 0; i < tiles.Count; i++)
        {
            if (measure)
            {
                Children[i].Measure(new Size(FreeformLayout.ContentWidth(tiles[i], width), double.PositiveInfinity));
            }

            heights[i] = Children[i].DesiredSize.Height;
        }

        return FreeformLayout.Arrange(tiles, heights, width);
    }
}
