using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Services;
using CleanCutPDF.Core.Workspaces;

namespace CleanCutPDF.Core.Tests;

public sealed class Phase6Tests : IDisposable
{
    private const int Surface = WorkspaceLayout.SurfaceWidth;

    private readonly TempDirectory _temp = new();
    private readonly AppPaths _paths;

    public Phase6Tests()
    {
        _paths = new AppPaths(Path.Combine(_temp.Path, "data"), Path.Combine(_temp.Path, "legacy"));
        _paths.EnsureCreated();
    }

    private static LayoutTile Tile(int x, int y, int width, int height) => new() { X = x, Y = y, Width = width, Height = height };

    // ───── Model ─────

    [Fact]
    public void Stacked_layout_is_one_full_width_column_in_field_order()
    {
        var layout = WorkspaceLayout.Stacked(["a", "b", "c"]);
        Assert.Equal(["a", "b", "c"], layout.Tiles.Keys);
        Assert.All(layout.Tiles.Values, t => Assert.Equal((0, Surface), (t.X, t.Width)));
        Assert.Equal([0, 72, 144], layout.Tiles.Values.Select(t => t.Y));
        Assert.True(layout.SnapToGrid);
        Assert.Equal(24, layout.GridSize);
    }

    [Fact]
    public void Sync_drops_unassigned_fields_adds_new_ones_at_the_bottom_and_repairs_tiles()
    {
        var layout = new WorkspaceLayout
        {
            GridSize = 500,
            Tiles =
            {
                ["a"] = Tile(0, 0, 360, 72),
                ["gone"] = Tile(360, 0, 360, 72),
                ["bad"] = Tile(-50, -10, 5000, 3)
            }
        };

        layout.Sync(["a", "bad", "new"]);

        Assert.Equal(["a", "bad", "new"], layout.Tiles.Keys.Order());
        Assert.Equal(64, layout.GridSize);
        var bad = layout.Tiles["bad"];
        Assert.Equal((0, 0, Surface, WorkspaceLayout.MinTileHeight), (bad.X, bad.Y, bad.Width, bad.Height));
        var added = layout.Tiles["new"];
        Assert.Equal((0, 72, Surface, 72), (added.X, added.Y, added.Width, added.Height)); // Under the lowest tile.
    }

    [Fact]
    public void Catalog_keeps_layouts_in_step_with_field_assignment()
    {
        var catalog = WorkspaceCatalog.CreateDefault();
        var legal = catalog.Find("Legal");
        Assert.Null(catalog.Resolve("Legal").Layout); // Automatic by default.

        legal.Layout = WorkspaceLayout.Stacked(legal.FieldKeys);
        legal.UnassignField("description");
        legal.AssignField("amount");

        // The form always gets a complete layout, even before the change is saved…
        var resolved = catalog.Resolve("Legal");
        Assert.Equal(resolved.Fields.Select(f => f.Key).Order(), resolved.Layout!.Tiles.Keys.Order());

        // …and it is a copy; editing it never changes the saved layout.
        resolved.Layout.Tiles["amount"].X = 99;

        catalog.Normalize(); // Runs on every save.
        Assert.DoesNotContain("description", legal.Layout.Tiles.Keys);
        var amount = legal.Layout.Tiles["amount"];
        Assert.Equal(0, amount.X);
        Assert.Equal(legal.Layout.Tiles.Values.Where(t => t != amount).Max(t => t.Bottom), amount.Y);

        // A layout left with no tiles is the automatic layout again.
        foreach (var key in legal.FieldKeys.ToList())
        {
            legal.UnassignField(key);
        }

        catalog.Normalize();
        Assert.Null(legal.Layout);
    }

    [Fact]
    public void Header_fields_stay_in_the_part_header_and_are_never_tiles()
    {
        var catalog = WorkspaceCatalog.CreateDefault();
        var accounting = catalog.Find("Accounting"); // revoked (header toggle), agency, description, date
        Assert.Equal(["agency", "description", "date"], catalog.LayoutFieldKeys(accounting));

        accounting.Layout = WorkspaceLayout.Stacked(accounting.FieldKeys); // e.g. an imported 1.x layout with a Revoked tile
        Assert.DoesNotContain("revoked", catalog.Resolve("Accounting").Layout!.Tiles.Keys);
        catalog.Normalize();
        Assert.Equal(["agency", "date", "description"], accounting.Layout.Tiles.Keys.Order());

        // Taking the toggle out of the header makes it a tile, at the bottom.
        catalog.Fields["revoked"].Placement = null;
        catalog.Normalize();
        Assert.Equal(accounting.Layout.Tiles.Values.Max(t => t.Y), accounting.Layout.Tiles["revoked"].Y);
    }

    [Fact]
    public void A_layout_nobody_changed_is_recognised_as_the_automatic_form()
    {
        string[] keys = ["a", "b", "c"];
        var layout = WorkspaceLayout.Stacked(keys);
        Assert.True(layout.IsStackedFor(keys));

        layout.SnapToGrid = false; // A preference, not a layout change.
        Assert.True(layout.IsStackedFor(keys));

        layout.Tiles["b"].Width = 360;
        Assert.False(layout.IsStackedFor(keys));
        layout.Tiles["b"].Width = WorkspaceLayout.SurfaceWidth;
        Assert.True(layout.IsStackedFor(keys));

        Assert.False(layout.IsStackedFor(["a", "c", "b"])); // Same column, different order.
        Assert.False(layout.IsStackedFor(["a", "b"]));
        Assert.False(layout.IsStackedFor(["a", "b", "c", "d"]));
    }

    [Fact]
    public async Task Layout_round_trips_through_workspaces_json_and_old_files_still_load()
    {
        var store = new WorkspaceStore(_paths);
        await store.LoadAsync();
        var legal = store.Catalog.Find("Legal");
        legal.Layout = new WorkspaceLayout
        {
            SnapToGrid = false,
            Tiles =
            {
                ["matter_number"] = Tile(0, 0, 360, 72), ["document_type"] = Tile(360, 0, 360, 72),
                ["description"] = Tile(0, 72, 720, 72), ["date"] = Tile(0, 144, 240, 96)
            }
        };
        await store.SaveAsync();

        var json = await File.ReadAllTextAsync(_paths.WorkspacesFile);
        Assert.Contains("\"layout\"", json);
        Assert.Contains("\"snap_to_grid\": false", json);
        Assert.DoesNotContain("\"right\"", json); // Computed values are not stored.
        Assert.DoesNotContain("\"bottom\"", json);

        var reloaded = new WorkspaceStore(_paths);
        await reloaded.LoadAsync();
        var layout = reloaded.Catalog.Find("Legal").Layout!;
        Assert.False(layout.SnapToGrid);
        var date = layout.Tiles["date"];
        Assert.Equal((0, 144, 240, 96), (date.X, date.Y, date.Width, date.Height));
        Assert.Null(reloaded.Catalog.Find("Accounting").Layout);

        // A file written before layouts existed (no "layout" key).
        await File.WriteAllTextAsync(_paths.WorkspacesFile,
            """{"fields": {}, "workspaces": [{"name": "Accounting", "field_keys": ["agency", "date"], "permanent": true}]}""");
        var old = new WorkspaceStore(_paths);
        await old.LoadAsync();
        Assert.Null(old.Catalog.Find("Accounting").Layout);
        Assert.Equal(["agency", "date"], old.Catalog.Find("Accounting").FieldKeys);
    }

    // ───── Designer editing ─────

    [Fact]
    public void Moving_snaps_to_the_grid_and_stays_on_the_surface()
    {
        var start = Tile(48, 48, 240, 72);

        var moved = LayoutEditing.Move(start, 30, 40, snap: true, grid: 24);
        Assert.Equal((72, 96, 240, 72), (moved.X, moved.Y, moved.Width, moved.Height));

        var free = LayoutEditing.Move(start, 30.4, 40.6, snap: false, grid: 24);
        Assert.Equal((78, 89), (free.X, free.Y));

        var clamped = LayoutEditing.Move(start, 5000, -5000, snap: true, grid: 24);
        Assert.Equal((Surface - 240, 0), (clamped.X, clamped.Y));
        Assert.Equal(0, LayoutEditing.Move(start, -5000, 0, snap: true, grid: 24).X);

        // Moving down is not limited: the surface grows.
        Assert.Equal(48 + 4800, LayoutEditing.Move(start, 0, 4800, snap: true, grid: 24).Y);
        Assert.Equal(48, start.X); // The starting tile is not changed.
    }

    [Fact]
    public void Resizing_respects_minimum_sizes_and_the_surface_edges()
    {
        var start = Tile(240, 96, 240, 72);

        var wider = LayoutEditing.Resize(start, TileEdges.Right, 100, 0, snap: true, grid: 24);
        Assert.Equal((240, 96, 336, 72), (wider.X, wider.Y, wider.Width, wider.Height));

        var corner = LayoutEditing.Resize(start, TileEdges.Right | TileEdges.Bottom, 5000, 50, snap: true, grid: 24);
        Assert.Equal((Surface - 240, 120), (corner.Width, corner.Height)); // Right edge stops at the surface.

        var fromLeft = LayoutEditing.Resize(start, TileEdges.Left, -100, 0, snap: true, grid: 24);
        Assert.Equal((144, 336), (fromLeft.X, fromLeft.Width)); // The right edge stays put.

        var tooNarrow = LayoutEditing.Resize(start, TileEdges.Left, 5000, 0, snap: true, grid: 24);
        Assert.Equal((480 - WorkspaceLayout.MinTileWidth, WorkspaceLayout.MinTileWidth), (tooNarrow.X, tooNarrow.Width));

        var tooShort = LayoutEditing.Resize(start, TileEdges.Top | TileEdges.Left, 0, 5000, snap: false, grid: 24);
        Assert.Equal((168 - WorkspaceLayout.MinTileHeight, WorkspaceLayout.MinTileHeight), (tooShort.Y, tooShort.Height));

        var squashed = LayoutEditing.Resize(start, TileEdges.Bottom, 0, -5000, snap: true, grid: 24);
        Assert.Equal(WorkspaceLayout.MinTileHeight, squashed.Height);
        Assert.Equal(0, LayoutEditing.Resize(start, TileEdges.Top, 0, -5000, snap: true, grid: 24).Y);
    }

    [Theory]
    [InlineData(100, 30, TileEdges.None)]
    [InlineData(2, 30, TileEdges.Left)]
    [InlineData(198, 30, TileEdges.Right)]
    [InlineData(100, 3, TileEdges.Top)]
    [InlineData(100, 70, TileEdges.Bottom)]
    [InlineData(1, 1, TileEdges.Left | TileEdges.Top)]
    [InlineData(199, 71, TileEdges.Right | TileEdges.Bottom)]
    public void Pointer_position_picks_move_or_the_edges_to_resize(double x, double y, TileEdges expected) =>
        Assert.Equal(expected, LayoutEditing.EdgesAt(x, y, 200, 72));

    // ───── Placing tiles in the form ─────

    [Fact]
    public void An_untouched_layout_is_placed_exactly_like_the_automatic_form()
    {
        // The automatic form stacks fields at their natural heights with nothing between them.
        var layout = WorkspaceLayout.Stacked(["a", "b", "c", "d"]);
        double[] natural = [62, 62, 48, 81];
        var rects = FreeformLayout.Arrange(layout.Tiles.Values.ToList(), natural, 500);

        Assert.Equal([0, 62, 124, 172], rects.Select(r => r.Y));
        Assert.Equal(natural, rects.Select(r => r.Height));
        Assert.All(rects, r => Assert.Equal((0, 500), (r.X, r.Width)));
    }

    [Fact]
    public void Tiles_keep_their_proportions_at_any_card_width()
    {
        var tiles = new[] { Tile(0, 0, 360, 72), Tile(360, 0, 360, 72), Tile(0, 72, 720, 72) };
        var content = new double[] { 60, 60, 60 };

        var narrow = FreeformLayout.Arrange(tiles, content, 400);
        Assert.Equal(0, narrow[0].X);
        Assert.Equal(200 - FreeformLayout.Gap, narrow[0].Width); // Left half, minus the gap to its neighbor.
        Assert.Equal(200, narrow[1].X);
        Assert.Equal(200, narrow[1].Width); // Reaches the right edge: no gap.
        Assert.Equal(400, narrow[2].Width);
        Assert.Equal([0, 0, 60], narrow.Select(r => r.Y));

        var wide = FreeformLayout.Arrange(tiles, content, 1440);
        Assert.Equal(720, wide[1].X);
        Assert.Equal(1440, wide[2].Width);
        Assert.Equal([0, 0, 60], wide.Select(r => r.Y)); // Vertical positions do not stretch.
    }

    [Fact]
    public void Rows_stay_lined_up_and_taller_content_moves_everything_under_it_down()
    {
        // Row 1: a | b. Row 2: c | d. Then an empty 24 px band, then e across both.
        var tiles = new[]
        {
            Tile(0, 0, 360, 72), Tile(360, 0, 360, 72), Tile(0, 72, 360, 72), Tile(360, 72, 360, 72), Tile(0, 168, 720, 72)
        };
        var rects = FreeformLayout.Arrange(tiles, [130, 60, 60, 60, 60], 720);

        Assert.Equal(130, rects[0].Height); // a needs more (notes, bigger text)…
        Assert.Equal(130, rects[1].Height); // …and b, beside it, shares the row.
        Assert.Equal([130, 130], [rects[2].Y, rects[3].Y]); // Row 2 starts together under row 1.
        Assert.Equal(130 + 60 + 24, rects[4].Y); // The empty band the user left is kept.

        // Nothing overlaps.
        for (var i = 0; i < tiles.Length; i++)
        {
            for (var j = i + 1; j < tiles.Length; j++)
            {
                var separate = rects[i].X + rects[i].Width <= rects[j].X + 0.01 || rects[j].X + rects[j].Width <= rects[i].X + 0.01
                               || rects[i].Bottom <= rects[j].Y + 0.01 || rects[j].Bottom <= rects[i].Y + 0.01;
                Assert.True(separate, $"tiles {i} and {j} overlap");
            }
        }
    }

    [Fact]
    public void A_tile_made_taller_than_normal_adds_that_much_space()
    {
        var rects = FreeformLayout.Arrange([Tile(0, 0, 720, 72 + 48), Tile(0, 120, 720, 72)], [60, 60], 720);
        Assert.Equal(60 + 48, rects[0].Height);
        Assert.Equal(108, rects[1].Y);

        // A tile made shorter than normal still gets what its field needs.
        var small = FreeformLayout.Arrange([Tile(0, 0, 720, 48), Tile(0, 48, 720, 72)], [60, 60], 720);
        Assert.Equal([0, 60], small.Select(r => r.Y));
    }

    [Fact]
    public void A_tall_tile_beside_two_short_ones_spans_both_rows()
    {
        // Left: one tile two rows high. Right: two tiles.
        var rects = FreeformLayout.Arrange([Tile(0, 0, 360, 144), Tile(360, 0, 360, 72), Tile(360, 72, 360, 72)], [60, 62, 62], 720);
        Assert.Equal([0, 0, 62], rects.Select(r => r.Y));
        Assert.Equal(60 + 72, rects[0].Height); // Its content plus the extra row it was given.
        Assert.Equal(132, rects[2].Bottom); // The right column ends level with it.
    }

    [Fact]
    public void Tiles_designed_on_top_of_each_other_are_separated()
    {
        var rects = FreeformLayout.Arrange([Tile(0, 0, 720, 96), Tile(120, 48, 300, 72)], [60, 60], 720);
        Assert.Equal(84, rects[0].Height);
        Assert.Equal(84, rects[1].Y);
    }

    [Fact]
    public void A_hidden_conditional_field_takes_no_space_just_like_the_automatic_form()
    {
        var tiles = new[] { Tile(0, 0, 720, 72), Tile(0, 72, 720, 72), Tile(0, 144, 720, 72) };
        var rects = FreeformLayout.Arrange(tiles, [60, 0, 60], 720);
        Assert.Equal(0, rects[1].Height);
        Assert.Equal(60, rects[2].Y); // The field under it moves up, as it does without a layout.
    }

    [Fact]
    public void Placement_starts_at_the_top_tile_and_handles_no_tiles()
    {
        var rects = FreeformLayout.Arrange([Tile(0, 240, 720, 72), Tile(0, 336, 720, 72)], [60, 60], 720);
        Assert.Equal([0, 84], rects.Select(r => r.Y)); // No blank band above the first tile; the 24 px gap is kept.
        Assert.Empty(FreeformLayout.Arrange([], [], 720));
    }

    // ───── 1.x import ─────

    [Fact]
    public async Task Legacy_freeform_layout_is_imported_onto_the_new_surface()
    {
        // The shape of a real 1.x layout: two fields side by side, then two full-width rows.
        var catalog = await ImportAsync("""
            {"workspaces": {
              "Accounting": {"field_keys": ["agency", "date"], "permanent": true, "custom_layout": null},
              "Testing": {"field_keys": ["agency", "matter_number", "date", "amount"], "layout_snap_to_grid": true,
                "custom_layout": {"enabled": true, "version": 3, "snap_to_grid": true, "grid_size": 24,
                  "surface": {"width": 663, "height": 420},
                  "elements": {"agency": {"x": 31, "y": 48, "width": 297, "height": 96},
                               "matter_number": {"x": 342, "y": 48, "width": 297, "height": 96},
                               "date": {"x": 31, "y": 192, "width": 606, "height": 96},
                               "amount": {"x": 24, "y": 312, "width": 614, "height": 96},
                               "unassigned": {"x": 0, "y": 500, "width": 300, "height": 96}}}},
              "Off": {"field_keys": ["agency"], "custom_layout": {"enabled": false, "elements": {"agency": {"x": 5, "y": 5, "width": 200, "height": 96}}}}
            }}
            """);

        Assert.Null(catalog.Find("Accounting").Layout);
        Assert.Null(catalog.Find("Off").Layout);

        var layout = catalog.Find("Testing").Layout!;
        Assert.True(layout.SnapToGrid);
        Assert.Equal(["agency", "amount", "date", "matter_number"], layout.Tiles.Keys.Order());

        var agency = layout.Tiles["agency"];
        var matter = layout.Tiles["matter_number"];
        var date = layout.Tiles["date"];
        var amount = layout.Tiles["amount"];

        // The used area becomes the whole surface: still side by side, about half each.
        Assert.Equal(agency.Y, matter.Y);
        Assert.Equal((0, 360), (agency.X, agency.Width));
        Assert.InRange(matter.Width, 330, 360);
        Assert.True(agency.Right <= matter.X);
        Assert.Equal(Surface, matter.Right);
        Assert.Equal((0, Surface), (amount.X, amount.Width));
        Assert.Equal((0, Surface), (date.X, date.Width));

        // Rows keep their order and 96 px rows become 72 px rows, starting at the top.
        Assert.Equal(0, agency.Y);
        Assert.Equal(72, agency.Height);
        Assert.True(date.Y >= agency.Bottom);
        Assert.True(amount.Y >= date.Bottom);
        Assert.All(layout.Tiles.Values, t => Assert.Equal(72, t.Height));

        // Snap to Grid was on, so every edge lands on the grid.
        Assert.All(layout.Tiles.Values, t => Assert.Equal((0, 0, 0, 0), (t.X % 24, t.Y % 24, t.Width % 24, t.Height % 24)));
        Assert.All(layout.Tiles.Values, t => Assert.InRange(t.Right, 0, Surface));
    }

    [Fact]
    public void Legacy_layout_saved_without_snapping_keeps_exact_proportions()
    {
        var tiles = FreeformLayout.FromLegacy(new Dictionary<string, LayoutTile>
        {
            ["a"] = Tile(31, 48, 297, 96), ["b"] = Tile(342, 48, 297, 96)
        });
        Assert.Equal((0, 0, 352, 72), (tiles["a"].X, tiles["a"].Y, tiles["a"].Width, tiles["a"].Height));
        Assert.Equal((368, Surface), (tiles["b"].X, tiles["b"].Right));
        Assert.Empty(FreeformLayout.FromLegacy(new Dictionary<string, LayoutTile>()));
    }

    [Fact]
    public async Task First_generation_grid_layout_is_migrated_like_1x_did()
    {
        var catalog = await ImportAsync("""
            {"workspaces": {"Accounting": {"field_keys": ["agency", "description", "date"], "permanent": true,
              "custom_layout": {"enabled": true, "field_positions": {
                "agency": {"row": 0, "col": 0, "span": 1}, "description": {"row": 0, "col": 1, "span": 2},
                "date": {"row": 1, "col": 0, "span": 3}}}}}}
            """);

        var layout = catalog.Find("Accounting").Layout!;
        var agency = layout.Tiles["agency"];
        var description = layout.Tiles["description"];
        var date = layout.Tiles["date"];
        Assert.Equal(agency.Y, description.Y); // Same row.
        Assert.True(agency.Right <= description.X);
        Assert.True(description.Width > agency.Width * 1.8); // Spans two of three columns.
        Assert.True(date.Y >= agency.Bottom);
        Assert.Equal((0, Surface), (date.X, date.Width));
    }

    private async Task<WorkspaceCatalog> ImportAsync(string settingsJson)
    {
        Directory.CreateDirectory(_paths.LegacyDataDirectory);
        await File.WriteAllTextAsync(Path.Combine(_paths.LegacyDataDirectory, "settings.json"), settingsJson);
        var import = await new LegacyImporter(_paths).ReadAsync();
        Assert.Empty(import.Warnings);
        return import.Catalog!;
    }

    public void Dispose() => _temp.Dispose();
}
