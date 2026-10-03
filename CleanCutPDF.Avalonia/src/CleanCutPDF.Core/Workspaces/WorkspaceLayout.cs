namespace CleanCutPDF.Core.Workspaces;

/// <summary>Where one field sits on the design surface (whole pixels, like 1.x).</summary>
public sealed class LayoutTile
{
    public int X { get; set; }
    public int Y { get; set; }
    public int Width { get; set; } = WorkspaceLayout.SurfaceWidth;
    public int Height { get; set; } = WorkspaceLayout.DefaultTileHeight;

    [System.Text.Json.Serialization.JsonIgnore]
    public int Right => X + Width;

    [System.Text.Json.Serialization.JsonIgnore]
    public int Bottom => Y + Height;

    public LayoutTile Clone() => (LayoutTile)MemberwiseClone();
}

/// <summary>
/// A workspace's custom form layout (the 1.x Workspace Layout Designer). The
/// design surface is always <see cref="SurfaceWidth"/> wide and stands for the
/// full width of a Part card, so a tile that covers the left half in the
/// designer covers the left half of the form. A workspace without a layout
/// uses the automatic stacked form.
/// </summary>
public sealed class WorkspaceLayout
{
    public const int SurfaceWidth = 720;
    public const int DefaultGridSize = 24;
    public const int MinTileWidth = 96;
    public const int MinTileHeight = 48;
    public const int DefaultTileHeight = 72;

    public bool SnapToGrid { get; set; } = true;
    public int GridSize { get; set; } = DefaultGridSize;

    /// <summary>Field key → tile.</summary>
    public Dictionary<string, LayoutTile> Tiles { get; set; } = new();

    /// <summary>The automatic form as tiles: every field full width, one under the other.</summary>
    public static WorkspaceLayout Stacked(IEnumerable<string> fieldKeys)
    {
        var layout = new WorkspaceLayout();
        var y = 0;
        foreach (var key in fieldKeys)
        {
            layout.Tiles[key] = new LayoutTile { Y = y };
            y += DefaultTileHeight;
        }

        return layout;
    }

    /// <summary>
    /// True when this is exactly the automatic form (every field full width,
    /// in order, at the normal height), so there is nothing custom to keep.
    /// </summary>
    public bool IsStackedFor(IReadOnlyList<string> fieldKeys)
    {
        var stacked = Stacked(fieldKeys);
        return Tiles.Count == stacked.Tiles.Count && stacked.Tiles.All(pair =>
            Tiles.TryGetValue(pair.Key, out var tile)
            && (tile.X, tile.Y, tile.Width, tile.Height) == (pair.Value.X, pair.Value.Y, pair.Value.Width, pair.Value.Height));
    }

    /// <summary>
    /// Makes the layout match the workspace's fields: tiles of fields that are
    /// no longer assigned are dropped (1.x: otherwise an unassigned field
    /// seemed to come back later), newly assigned fields get a full-width tile
    /// at the bottom, and every tile is kept on the surface.
    /// </summary>
    public void Sync(IReadOnlyList<string> fieldKeys)
    {
        GridSize = Math.Clamp(GridSize, 8, 64);
        foreach (var stale in Tiles.Keys.Where(k => !fieldKeys.Contains(k)).ToList())
        {
            Tiles.Remove(stale);
        }

        foreach (var tile in Tiles.Values)
        {
            tile.Width = Math.Clamp(tile.Width, MinTileWidth, SurfaceWidth);
            tile.Height = Math.Max(MinTileHeight, tile.Height);
            tile.X = Math.Clamp(tile.X, 0, SurfaceWidth - tile.Width);
            tile.Y = Math.Max(0, tile.Y);
        }

        foreach (var key in fieldKeys.Where(k => !Tiles.ContainsKey(k)))
        {
            Tiles[key] = new LayoutTile { Y = Tiles.Count == 0 ? 0 : Tiles.Values.Max(t => t.Bottom) };
        }
    }

    public WorkspaceLayout Clone() => new()
    {
        SnapToGrid = SnapToGrid,
        GridSize = GridSize,
        Tiles = Tiles.ToDictionary(pair => pair.Key, pair => pair.Value.Clone())
    };
}

[Flags]
public enum TileEdges
{
    None = 0,
    Left = 1,
    Top = 2,
    Right = 4,
    Bottom = 8
}

/// <summary>Dragging and resizing tiles in the designer (1.x rules: optional grid snap, minimum sizes, kept on the surface).</summary>
public static class LayoutEditing
{
    public static int Snap(double value, bool snap, int grid) =>
        snap ? (int)Math.Round(value / grid, MidpointRounding.AwayFromZero) * grid : (int)Math.Round(value);

    /// <summary>The tile after dragging it by (dx, dy) from where the drag started.</summary>
    public static LayoutTile Move(LayoutTile start, double dx, double dy, bool snap, int grid)
    {
        var tile = start.Clone();
        tile.X = Math.Clamp(Snap(start.X + dx, snap, grid), 0, WorkspaceLayout.SurfaceWidth - tile.Width);
        tile.Y = Math.Max(0, Snap(start.Y + dy, snap, grid));
        return tile;
    }

    /// <summary>The tile after dragging the given edges by (dx, dy) from where the drag started.</summary>
    public static LayoutTile Resize(LayoutTile start, TileEdges edges, double dx, double dy, bool snap, int grid)
    {
        int left = start.X, top = start.Y, right = start.Right, bottom = start.Bottom;
        if (edges.HasFlag(TileEdges.Left))
        {
            left = Math.Clamp(Snap(start.X + dx, snap, grid), 0, right - WorkspaceLayout.MinTileWidth);
        }

        if (edges.HasFlag(TileEdges.Right))
        {
            right = Math.Clamp(Snap(start.Right + dx, snap, grid), left + WorkspaceLayout.MinTileWidth, WorkspaceLayout.SurfaceWidth);
        }

        if (edges.HasFlag(TileEdges.Top))
        {
            top = Math.Clamp(Snap(start.Y + dy, snap, grid), 0, bottom - WorkspaceLayout.MinTileHeight);
        }

        if (edges.HasFlag(TileEdges.Bottom))
        {
            bottom = Math.Max(top + WorkspaceLayout.MinTileHeight, Snap(start.Bottom + dy, snap, grid));
        }

        return new LayoutTile { X = left, Y = top, Width = right - left, Height = bottom - top };
    }

    /// <summary>Which edges a pointer at (x, y) inside a tile of the given size would resize.</summary>
    public static TileEdges EdgesAt(double x, double y, double width, double height, double margin = 8)
    {
        var edges = TileEdges.None;
        if (x <= margin)
        {
            edges |= TileEdges.Left;
        }
        else if (x >= width - margin)
        {
            edges |= TileEdges.Right;
        }

        if (y <= margin)
        {
            edges |= TileEdges.Top;
        }
        else if (y >= height - margin)
        {
            edges |= TileEdges.Bottom;
        }

        return edges;
    }
}

public readonly record struct LayoutRect(double X, double Y, double Width, double Height)
{
    public double Bottom => Y + Height;
}

/// <summary>
/// Places tiles in a Part card so that an untouched layout looks exactly like
/// the automatic form. Horizontally the surface is stretched to the card, so
/// proportions are what was designed. Vertically the design is treated as
/// rows: a tile of the normal height is as tall as its field needs (so stacked
/// fields sit as close as in the automatic form), a taller tile adds that much
/// extra space, empty bands between tiles keep their size, and tiles that
/// start or end on the same line in the designer still do in the form. A field
/// that needs more height (larger text, notes) moves everything under it down
/// instead of painting over it, which was a recurring 1.x problem.
/// </summary>
public static class FreeformLayout
{
    /// <summary>Space between tiles that sit side by side.</summary>
    public const double Gap = 8;

    /// <summary>The width a tile's content is given in a card of this width.</summary>
    public static double ContentWidth(LayoutTile tile, double availableWidth)
    {
        var scale = availableWidth / WorkspaceLayout.SurfaceWidth;
        var gap = tile.Right >= WorkspaceLayout.SurfaceWidth ? 0 : Gap;
        return Math.Max(40, tile.Width * scale - gap);
    }

    /// <param name="tiles">Tiles in any order.</param>
    /// <param name="contentHeights">What each tile's content needs at <see cref="ContentWidth"/>; 0 = hidden (a conditional field).</param>
    /// <returns>One rectangle per tile, in the same order.</returns>
    public static IReadOnlyList<LayoutRect> Arrange(IReadOnlyList<LayoutTile> tiles, IReadOnlyList<double> contentHeights,
        double availableWidth)
    {
        var rects = new LayoutRect[tiles.Count];
        if (tiles.Count == 0)
        {
            return rects;
        }

        // What each tile must be given: its content, plus whatever the user added beyond the normal height.
        var needed = tiles.Select((tile, i) => contentHeights[i] <= 0
            ? 0
            : contentHeights[i] + Math.Max(0, tile.Height - WorkspaceLayout.DefaultTileHeight)).ToList();

        // Every line where a tile starts or ends in the design gets a position in the form.
        var lines = tiles.SelectMany(t => new[] { t.Y, t.Bottom }).Distinct().Order().ToList();
        var position = new Dictionary<int, double> { [lines[0]] = 0 };
        for (var k = 1; k < lines.Count; k++)
        {
            int previous = lines[k - 1], line = lines[k];
            var isEmptyBand = !tiles.Any(t => t.Y < line && t.Bottom > previous);
            var y = position[previous] + (isEmptyBand ? line - previous : 0);
            for (var i = 0; i < tiles.Count; i++)
            {
                if (tiles[i].Bottom == line)
                {
                    y = Math.Max(y, position[tiles[i].Y] + needed[i]);
                }
            }

            position[line] = y;
        }

        var scale = availableWidth / WorkspaceLayout.SurfaceWidth;
        var placed = new List<int>();
        foreach (var i in Enumerable.Range(0, tiles.Count).OrderBy(i => tiles[i].Y).ThenBy(i => tiles[i].X))
        {
            var tile = tiles[i];
            var hidden = needed[i] <= 0;
            var top = position[tile.Y];
            if (!hidden)
            {
                // Tiles drawn on top of each other in the designer are separated here.
                foreach (var j in placed.Where(j => tiles[j].X < tile.Right && tile.X < tiles[j].Right))
                {
                    top = Math.Max(top, rects[j].Bottom);
                }

                placed.Add(i);
            }

            rects[i] = new LayoutRect(tile.X * scale, top, ContentWidth(tile, availableWidth),
                hidden ? 0 : position[tile.Bottom] - position[tile.Y]);
        }

        return rects;
    }

    /// <summary>
    /// Converts 1.x rectangles (any surface size; only the used area mattered)
    /// to this surface: the used width becomes the full width, the top tile
    /// starts at 0, and heights shrink from the 1.x 96-pixel rows to rows of
    /// <see cref="WorkspaceLayout.DefaultTileHeight"/>.
    /// </summary>
    /// <param name="snapTo">Grid size to line the converted edges up on (the layout had Snap to Grid on), or 0.</param>
    public static Dictionary<string, LayoutTile> FromLegacy(IReadOnlyDictionary<string, LayoutTile> legacy, int snapTo = 0)
    {
        int Edge(double value) => snapTo > 0 ? LayoutEditing.Snap(value, true, snapTo) : (int)Math.Round(value);

        var result = new Dictionary<string, LayoutTile>();
        if (legacy.Count == 0)
        {
            return result;
        }

        const double LegacyRowHeight = 96;
        var minX = legacy.Values.Min(t => t.X);
        var minY = legacy.Values.Min(t => t.Y);
        var usedWidth = Math.Max(1, legacy.Values.Max(t => t.Right) - minX);
        var scaleX = (double)WorkspaceLayout.SurfaceWidth / usedWidth;
        var scaleY = WorkspaceLayout.DefaultTileHeight / LegacyRowHeight;
        foreach (var (key, tile) in legacy)
        {
            var left = Edge((tile.X - minX) * scaleX);
            var right = Math.Min(WorkspaceLayout.SurfaceWidth, Edge((tile.Right - minX) * scaleX));
            var top = Edge((tile.Y - minY) * scaleY);
            var bottom = Edge((tile.Bottom - minY) * scaleY);
            result[key] = new LayoutTile
            {
                X = left, Y = top,
                Width = Math.Max(WorkspaceLayout.MinTileWidth, right - left),
                Height = Math.Max(WorkspaceLayout.MinTileHeight, bottom - top)
            };
        }

        return result;
    }
}
