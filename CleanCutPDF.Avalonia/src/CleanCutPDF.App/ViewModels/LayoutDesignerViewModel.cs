using Avalonia.Media;
using CleanCutPDF.Core.Workspaces;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace CleanCutPDF.App.ViewModels;

/// <summary>One field tile on the design surface, drawn like the field it stands for.</summary>
public sealed partial class DesignerTileViewModel(FieldDefinition field, LayoutTile tile) : ObservableObject
{
    public string Key { get; } = field.Key;
    public string Label { get; } = field.Label;

    /// <summary>The label as the form shows it (date format, required mark).</summary>
    public string DisplayLabel { get; } =
        field.Label + (field.Type == FieldType.Date ? $" ({field.DateFormat})" : "") + (field.Required ? " *" : "");

    public string Placeholder { get; } = field.Type == FieldType.Choice ? "Select..." : field.Placeholder;

    public bool IsBoolean { get; } = field.IsBoolean;
    public bool IsDate { get; } = field.Type == FieldType.Date;
    public bool IsChoice { get; } = field.Type == FieldType.Choice;

    /// <summary>The field's own label color, when it has one.</summary>
    public IBrush? Accent { get; } =
        !string.IsNullOrWhiteSpace(field.Color) && Color.TryParse(field.Color, out var color) ? new SolidColorBrush(color) : null;

    public bool HasAccent => Accent is not null;

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(WidthText))]
    public partial int X { get; set; } = tile.X;

    [ObservableProperty]
    public partial int Y { get; set; } = tile.Y;

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(WidthText))]
    public partial int Width { get; set; } = tile.Width;

    [ObservableProperty]
    public partial int Height { get; set; } = tile.Height;

    public string WidthText => $"{Width * 100 / WorkspaceLayout.SurfaceWidth}%";

    public LayoutTile ToTile() => new() { X = X, Y = Y, Width = Width, Height = Height };

    public void Apply(LayoutTile tile)
    {
        X = tile.X;
        Y = tile.Y;
        Width = tile.Width;
        Height = tile.Height;
    }

    // Used as the accessible name read by screen readers.
    public override string ToString() => $"{Label} tile";
}

/// <summary>
/// The Workspace Layout Designer (1.x "Workspace Designer"): drag field tiles
/// anywhere on a grid and resize them from an edge or corner. It opens showing
/// the form as it is now, and saving without changing anything changes
/// nothing. Nothing is applied until Save Layout.
/// </summary>
public sealed partial class LayoutDesignerViewModel : ObservableObject
{
    private readonly IReadOnlyList<string> _keys;
    private DesignerTileViewModel? _dragged;
    private LayoutTile? _dragStart;
    private TileEdges _dragEdges;

    public LayoutDesignerViewModel(ResolvedWorkspace workspace, WorkspaceLayout? current)
    {
        WorkspaceName = workspace.Name;

        // Header toggles stay in the Part header; the tiles are the fields under it.
        var body = workspace.Fields.Where(f => !f.IsHeaderField).ToList();
        HeaderFields = workspace.Fields.Where(f => f.IsHeaderField).Select(f => f.Label).ToList();
        _keys = body.Select(f => f.Key).ToList();

        var layout = current?.Clone() ?? WorkspaceLayout.Stacked(_keys);
        layout.Sync(_keys);
        SnapToGrid = layout.SnapToGrid;
        GridSize = layout.GridSize;
        Tiles = body.Select(f => new DesignerTileViewModel(f, layout.Tiles[f.Key])).ToList();
        foreach (var tile in Tiles)
        {
            tile.PropertyChanged += (_, _) =>
            {
                OnPropertyChanged(nameof(SurfaceHeight));
                OnPropertyChanged(nameof(IsAutomatic));
                OnPropertyChanged(nameof(StatusText));
            };
        }
    }

    public string WorkspaceName { get; }

    public string Title => $"{WorkspaceName} Layout Designer";

    /// <summary>Labels of the fields that stay in the Part header (shown, but not movable).</summary>
    public IReadOnlyList<string> HeaderFields { get; }

    public bool HasHeaderFields => HeaderFields.Count > 0;

    public int SurfaceWidth => WorkspaceLayout.SurfaceWidth;

    /// <summary>Always leaves room under the lowest tile to drag things further down.</summary>
    public int SurfaceHeight => Math.Max(360, (Tiles.Count == 0 ? 0 : Tiles.Max(t => t.Y + t.Height)) + 192);

    public IReadOnlyList<DesignerTileViewModel> Tiles { get; }

    public int GridSize { get; }

    [ObservableProperty]
    public partial bool SnapToGrid { get; set; }

    [ObservableProperty]
    public partial DesignerTileViewModel? SelectedTile { get; set; }

    /// <summary>True while the tiles are exactly the automatic stacked form.</summary>
    public bool IsAutomatic => Build().IsStackedFor(_keys);

    public string StatusText => IsAutomatic
        ? "This is the automatic layout. Saving now leaves the form exactly as it is."
        : "Custom layout. Fields you have not moved look the same as before.";

    /// <summary>True once Save Layout was chosen.</summary>
    public bool Saved { get; private set; }

    public event EventHandler? CloseRequested;

    public WorkspaceLayout Build() => new()
    {
        SnapToGrid = SnapToGrid,
        GridSize = GridSize,
        Tiles = Tiles.ToDictionary(t => t.Key, t => t.ToTile())
    };

    /// <summary>What to store: null when the tiles are the automatic form, so the workspace stays on Automatic.</summary>
    public WorkspaceLayout? Result() => IsAutomatic ? null : Build();

    // ───── Pointer ─────

    /// <summary>Starts moving (no edges) or resizing a tile.</summary>
    public void BeginDrag(DesignerTileViewModel tile, TileEdges edges)
    {
        SelectedTile = tile;
        _dragged = tile;
        _dragStart = tile.ToTile();
        _dragEdges = edges;
    }

    /// <summary>Updates the dragged tile; (dx, dy) is the pointer's distance from where the drag started.</summary>
    public void DragTo(double dx, double dy)
    {
        if (_dragged is null || _dragStart is null)
        {
            return;
        }

        _dragged.Apply(_dragEdges == TileEdges.None
            ? LayoutEditing.Move(_dragStart, dx, dy, SnapToGrid, GridSize)
            : LayoutEditing.Resize(_dragStart, _dragEdges, dx, dy, SnapToGrid, GridSize));
    }

    public void EndDrag()
    {
        _dragged = null;
        _dragStart = null;
    }

    public bool IsDragging => _dragged is not null;

    // ───── Keyboard ─────

    /// <summary>Arrow keys: moves the selected tile one step (a grid square, or one pixel when <paramref name="fine"/> or snapping is off).</summary>
    public void Nudge(int dx, int dy, bool fine)
    {
        if (SelectedTile is { } tile)
        {
            var step = Step(fine);
            tile.Apply(LayoutEditing.Move(tile.ToTile(), dx * step, dy * step, snap: false, GridSize));
        }
    }

    /// <summary>Shift+arrow keys: resizes the selected tile from its right and bottom edges.</summary>
    public void NudgeSize(int dx, int dy, bool fine)
    {
        if (SelectedTile is { } tile)
        {
            var step = Step(fine);
            tile.Apply(LayoutEditing.Resize(tile.ToTile(), TileEdges.Right | TileEdges.Bottom, dx * step, dy * step,
                snap: false, GridSize));
        }
    }

    private int Step(bool fine) => SnapToGrid && !fine ? GridSize : 1;

    // ───── Commands ─────

    /// <summary>Back to the automatic form: every field full width, in the workspace's field order.</summary>
    [RelayCommand]
    private void StackAll()
    {
        var stacked = WorkspaceLayout.Stacked(_keys);
        foreach (var tile in Tiles)
        {
            tile.Apply(stacked.Tiles[tile.Key]);
        }
    }

    [RelayCommand]
    private void Save()
    {
        Saved = true;
        CloseRequested?.Invoke(this, EventArgs.Empty);
    }

    [RelayCommand]
    private void Cancel() => CloseRequested?.Invoke(this, EventArgs.Empty);
}
