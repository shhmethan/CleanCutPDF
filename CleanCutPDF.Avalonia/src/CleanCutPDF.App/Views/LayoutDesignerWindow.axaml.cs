using Avalonia;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.VisualTree;
using CleanCutPDF.App.ViewModels;
using CleanCutPDF.Core.Workspaces;

namespace CleanCutPDF.App.Views;

public partial class LayoutDesignerWindow : Window
{
    private Point _dragOrigin;

    public LayoutDesignerWindow()
    {
        InitializeComponent();

        // The list box selects on press; these also run so a press can start a drag.
        Surface.AddHandler(PointerPressedEvent, OnPointerPressed, RoutingStrategies.Bubble, handledEventsToo: true);
        Surface.AddHandler(PointerMovedEvent, OnPointerMoved, RoutingStrategies.Bubble, handledEventsToo: true);
        Surface.AddHandler(PointerReleasedEvent, OnPointerReleased, RoutingStrategies.Bubble, handledEventsToo: true);
        Surface.AddHandler(PointerCaptureLostEvent, (_, _) => ViewModel?.EndDrag(), RoutingStrategies.Bubble, handledEventsToo: true);
        AddHandler(KeyDownEvent, OnKeyDown, RoutingStrategies.Tunnel);

        DataContextChanged += (_, _) =>
        {
            if (ViewModel is { } vm)
            {
                vm.CloseRequested += (_, _) => Close();
            }
        };
    }

    private LayoutDesignerViewModel? ViewModel => DataContext as LayoutDesignerViewModel;

    /// <summary>The tile under the pointer and which of its edges the pointer is on.</summary>
    private (DesignerTileViewModel Tile, TileEdges Edges)? Hit(PointerEventArgs e)
    {
        var item = (e.Source as Visual)?.FindAncestorOfType<ListBoxItem>(includeSelf: true);
        if (item?.DataContext is not DesignerTileViewModel tile)
        {
            return null;
        }

        var position = e.GetPosition(item);
        return (tile, LayoutEditing.EdgesAt(position.X, position.Y, item.Bounds.Width, item.Bounds.Height));
    }

    private void OnPointerPressed(object? sender, PointerPressedEventArgs e)
    {
        if (ViewModel is not { } vm || !e.GetCurrentPoint(Surface).Properties.IsLeftButtonPressed || Hit(e) is not { } hit)
        {
            return;
        }

        _dragOrigin = e.GetPosition(Surface);
        vm.BeginDrag(hit.Tile, hit.Edges);
        e.Pointer.Capture(Surface);
    }

    private void OnPointerMoved(object? sender, PointerEventArgs e)
    {
        if (ViewModel is not { } vm)
        {
            return;
        }

        if (vm.IsDragging)
        {
            var position = e.GetPosition(Surface);
            vm.DragTo(position.X - _dragOrigin.X, position.Y - _dragOrigin.Y);
        }
        else
        {
            Surface.Cursor = Hit(e) is { } hit ? CursorFor(hit.Edges) : Cursor.Default;
        }
    }

    private void OnPointerReleased(object? sender, PointerReleasedEventArgs e)
    {
        ViewModel?.EndDrag();
        e.Pointer.Capture(null);
    }

    private static Cursor CursorFor(TileEdges edges) => new(edges switch
    {
        TileEdges.Left | TileEdges.Top => StandardCursorType.TopLeftCorner,
        TileEdges.Right | TileEdges.Bottom => StandardCursorType.BottomRightCorner,
        TileEdges.Right | TileEdges.Top => StandardCursorType.TopRightCorner,
        TileEdges.Left | TileEdges.Bottom => StandardCursorType.BottomLeftCorner,
        TileEdges.Left or TileEdges.Right => StandardCursorType.SizeWestEast,
        TileEdges.Top or TileEdges.Bottom => StandardCursorType.SizeNorthSouth,
        _ => StandardCursorType.SizeAll
    });

    private void OnKeyDown(object? sender, KeyEventArgs e)
    {
        if (ViewModel is not { SelectedTile: not null } vm)
        {
            return;
        }

        var (dx, dy) = e.Key switch
        {
            Key.Left => (-1, 0),
            Key.Right => (1, 0),
            Key.Up => (0, -1),
            Key.Down => (0, 1),
            _ => (0, 0)
        };
        if (dx == 0 && dy == 0)
        {
            return;
        }

        var fine = e.KeyModifiers.HasFlag(KeyModifiers.Control);
        if (e.KeyModifiers.HasFlag(KeyModifiers.Shift))
        {
            vm.NudgeSize(dx, dy, fine);
        }
        else
        {
            vm.Nudge(dx, dy, fine);
        }

        e.Handled = true; // Otherwise the list would move the selection to another tile.
    }
}
