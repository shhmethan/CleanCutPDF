using CleanCutPDF.App.ViewModels;
using CleanCutPDF.App.ViewModels.Editor;
using CleanCutPDF.Core.Pdf;
using CleanCutPDF.Core.Workspaces;

namespace CleanCutPDF.App.Tests;

public sealed class LayoutDesignerTests
{
    private static readonly DateOnly Today = new(2026, 10, 2);
    private static readonly PageRange[] TwoParts = [new(0, 1), new(3, 3)];

    private static (WorkspaceCatalog Catalog, WorkspaceDefinition Accounting) Catalog()
    {
        var catalog = WorkspaceCatalog.CreateDefault();
        return (catalog, catalog.Find("Accounting"));
    }

    private static LayoutDesignerViewModel Designer(WorkspaceCatalog catalog) =>
        new(catalog.Resolve("Accounting"), catalog.Find("Accounting").Layout);

    private static WorkspaceFormViewModel Form(WorkspaceCatalog catalog) =>
        new(catalog.Resolve("Accounting"), TwoParts, null, _ => { }, Today);

    [Fact]
    public void Designer_opens_showing_the_form_as_it_is()
    {
        var (catalog, accounting) = Catalog();
        var designer = Designer(catalog);

        Assert.Equal("Accounting Layout Designer", designer.Title);
        Assert.Equal(["Revoked"], designer.HeaderFields); // Stays in the Part header; not a tile.
        Assert.Equal(["agency", "description", "date"], designer.Tiles.Select(t => t.Key));
        Assert.Equal([0, 72, 144], designer.Tiles.Select(t => t.Y));
        Assert.All(designer.Tiles, t => Assert.Equal((0, 720), (t.X, t.Width)));
        Assert.True(designer.IsAutomatic);
        Assert.Contains("automatic layout", designer.StatusText);
        Assert.True(designer.SnapToGrid);
        Assert.False(designer.Saved);
        Assert.Null(accounting.Layout);

        Assert.Equal("Agency Code tile", designer.Tiles[0].ToString());
        Assert.Equal("Date (M-D-YYYY)", designer.Tiles[2].DisplayLabel); // Drawn like the real field.
        Assert.True(designer.Tiles[2].IsDate);
    }

    [Fact]
    public void Saving_without_changing_anything_keeps_the_automatic_form()
    {
        var (catalog, accounting) = Catalog();
        var designer = Designer(catalog);
        designer.SnapToGrid = false; // Not a layout change.
        designer.SaveCommand.Execute(null);

        Assert.True(designer.Saved);
        Assert.Null(designer.Result());

        accounting.Layout = designer.Result();
        var part = Form(catalog).Parts[0];
        Assert.False(part.IsFreeform);
        Assert.Equal(["revoked"], part.HeaderFields.Select(f => f.Key));
        Assert.Equal(["agency", "description", "date"], part.BodyFields.Select(f => f.Key));
    }

    [Fact]
    public void Moving_a_field_and_putting_it_back_is_automatic_again()
    {
        var (catalog, _) = Catalog();
        var designer = Designer(catalog);
        var changes = new List<string?>();
        designer.PropertyChanged += (_, e) => changes.Add(e.PropertyName);

        designer.SelectedTile = designer.Tiles[0];
        designer.NudgeSize(-15, 0, fine: false);
        Assert.False(designer.IsAutomatic);
        Assert.NotNull(designer.Result());
        Assert.Contains(nameof(LayoutDesignerViewModel.StatusText), changes);

        designer.NudgeSize(15, 0, fine: false);
        Assert.True(designer.IsAutomatic);

        designer.Nudge(0, 5, fine: false);
        designer.StackAllCommand.Execute(null); // "Back to Automatic"
        Assert.True(designer.IsAutomatic);
        Assert.Null(designer.Result());
    }

    [Fact]
    public void Dragging_moves_and_resizes_with_snapping()
    {
        var (catalog, _) = Catalog();
        var designer = Designer(catalog);
        var agency = designer.Tiles[0];

        // Shrink Agency to the left half by dragging its right edge.
        designer.BeginDrag(agency, TileEdges.Right);
        Assert.Same(agency, designer.SelectedTile);
        designer.DragTo(-350, 0);
        designer.DragTo(-365, 9); // Later moves are measured from where the drag began.
        designer.EndDrag();
        Assert.Equal((0, 0, 360, 72), (agency.X, agency.Y, agency.Width, agency.Height));
        Assert.Equal("50%", agency.WidthText);

        // Put Description beside it.
        var description = designer.Tiles[1];
        designer.BeginDrag(description, TileEdges.Left);
        designer.DragTo(355, 0);
        designer.EndDrag();
        designer.BeginDrag(description, TileEdges.None);
        designer.DragTo(0, -70);
        designer.EndDrag();
        Assert.Equal((360, 0, 360, 72), (description.X, description.Y, description.Width, description.Height));

        // After the drag ends, pointer movement does nothing.
        designer.DragTo(100, 100);
        Assert.Equal(360, description.X);

        // Without snapping, positions are exact.
        designer.SnapToGrid = false;
        designer.BeginDrag(agency, TileEdges.None);
        designer.DragTo(0, 5);
        designer.EndDrag();
        Assert.Equal(5, agency.Y);
    }

    [Fact]
    public void Keyboard_moves_and_resizes_the_selected_tile()
    {
        var (catalog, _) = Catalog();
        var designer = Designer(catalog);
        var date = designer.Tiles[2];

        designer.Nudge(0, 1, fine: false); // Nothing selected: nothing happens.
        Assert.Equal(144, date.Y);

        designer.SelectedTile = date;
        designer.Nudge(0, 1, fine: false);
        Assert.Equal(168, date.Y); // One grid square.
        designer.Nudge(0, -1, fine: true);
        Assert.Equal(167, date.Y); // One pixel.
        designer.NudgeSize(-10, 1, fine: false);
        Assert.Equal((720 - 240, 96), (date.Width, date.Height));
        designer.Nudge(1, 0, fine: false);
        Assert.Equal(24, date.X);

        var height = designer.SurfaceHeight;
        designer.Nudge(0, 20, fine: false);
        Assert.True(designer.SurfaceHeight > height); // The surface grows as tiles move down.
    }

    [Fact]
    public void A_changed_layout_is_saved_reopened_and_used_by_the_form()
    {
        var (catalog, accounting) = Catalog();
        var designer = Designer(catalog);
        var closed = 0;
        designer.CloseRequested += (_, _) => closed++;

        designer.SelectedTile = designer.Tiles[0];
        designer.NudgeSize(-15, 0, fine: false); // Agency: 360 wide.
        designer.SaveCommand.Execute(null);
        Assert.Equal(1, closed);

        accounting.Layout = designer.Result();
        Assert.Equal(360, accounting.Layout!.Tiles["agency"].Width);
        Assert.DoesNotContain("revoked", accounting.Layout.Tiles.Keys);

        var reopened = Designer(catalog);
        Assert.Equal(360, reopened.Tiles[0].Width);
        Assert.False(reopened.IsAutomatic);

        var part = Form(catalog).Parts[1];
        Assert.True(part.IsFreeform);
        Assert.Equal(["revoked"], part.HeaderFields.Select(f => f.Key)); // Still in the header.
        Assert.Empty(part.BodyFields);
        Assert.Equal(["agency", "description", "date"], part.FreeformFields.Select(f => f.Key));
        Assert.Equal(360, part.Field("agency")!.Tile!.Width);
        Assert.Null(part.Field("revoked")!.Tile);

        var cancelled = Designer(catalog);
        cancelled.CancelCommand.Execute(null);
        Assert.False(cancelled.Saved);
    }

    [Fact]
    public void Values_defaults_and_autofill_are_the_same_with_a_custom_layout()
    {
        var (catalog, accounting) = Catalog();
        var automatic = Form(catalog);
        Assert.All(automatic.Parts[0].Fields, f => Assert.Null(f.Tile));
        Assert.Empty(automatic.Parts[0].FreeformFields);

        accounting.Layout = WorkspaceLayout.Stacked(catalog.LayoutFieldKeys(accounting));
        accounting.Layout.Tiles["agency"].Width = 360;
        var freeform = Form(catalog);

        Assert.Equal("POA", freeform.Parts[1].Field("description")!.Value);
        freeform.Parts[0].Field("agency")!.Value = "F";
        Assert.Equal("F", freeform.Parts[1].Field("agency")!.Value);
        freeform.Parts[0].Field("revoked")!.Value = "true";
        Assert.Equal("true", freeform.Parts[1].Field("revoked")!.Value);
        Assert.Equal(automatic.Capture()[0].Keys.Order(), freeform.Capture()[0].Keys.Order());
    }
}
