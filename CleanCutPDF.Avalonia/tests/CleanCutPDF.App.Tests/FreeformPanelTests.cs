using Avalonia;
using Avalonia.Controls;
using CleanCutPDF.App.Controls;
using CleanCutPDF.App.ViewModels.Editor;
using CleanCutPDF.Core.Workspaces;

namespace CleanCutPDF.App.Tests;

/// <summary>The panel that draws custom layouts, compared with the panel the automatic form uses.</summary>
public sealed class FreeformPanelTests
{
    private const double CardWidth = 537; // Deliberately not the designer's 720.

    // Field heights as they come out of the real templates (text, date with notes, toggle, …).
    private static readonly double[] Heights = [62, 62, 95, 40, 62];

    private static List<Rect> Layout(Panel panel, WorkspaceLayout? layout)
    {
        var keys = Heights.Select((_, i) => $"f{i}").ToList();
        for (var i = 0; i < Heights.Length; i++)
        {
            var field = FieldViewModel.Create(new FieldDefinition { Key = keys[i], Label = keys[i] }, [],
                layout?.Tiles[keys[i]]);
            panel.Children.Add(new Border { Height = Heights[i], DataContext = field });
        }

        panel.Measure(new Size(CardWidth, double.PositiveInfinity));
        panel.Arrange(new Rect(0, 0, CardWidth, panel.DesiredSize.Height));
        return panel.Children.Select(c => c.Bounds).ToList();
    }

    private static WorkspaceLayout Stacked() => WorkspaceLayout.Stacked(Heights.Select((_, i) => $"f{i}"));

    [Fact]
    public void An_untouched_layout_puts_every_field_exactly_where_the_automatic_form_does()
    {
        var automaticPanel = new StackPanel();
        var automatic = Layout(automaticPanel, null);
        var customPanel = new FreeformPanel();
        var custom = Layout(customPanel, Stacked());

        Assert.Equal(automatic, custom); // Same position and size for every field.
        Assert.Equal(automaticPanel.DesiredSize.Height, customPanel.DesiredSize.Height);
        Assert.Equal(Heights.Sum(), customPanel.DesiredSize.Height);
    }

    [Fact]
    public void Changing_one_field_leaves_the_fields_above_and_below_where_they_were()
    {
        var automatic = Layout(new StackPanel(), null);

        // Make the second field half width; nothing else is touched.
        var layout = Stacked();
        layout.Tiles["f1"].Width = 360;
        var custom = Layout(new FreeformPanel(), layout);

        Assert.Equal(automatic[1].Y, custom[1].Y);
        Assert.Equal(CardWidth / 2 - FreeformLayout.Gap, custom[1].Width, tolerance: 0.5); // Whole pixels on screen.
        foreach (var i in new[] { 0, 2, 3, 4 })
        {
            Assert.Equal(automatic[i], custom[i]);
        }
    }

    [Fact]
    public void Two_fields_side_by_side_share_a_row_and_the_rest_close_up()
    {
        var layout = Stacked();
        layout.Tiles["f0"].Width = 360;
        layout.Tiles["f1"] = new LayoutTile { X = 360, Y = 0, Width = 360, Height = 72 };
        // f2…f4 stay where the designer left them (y = 144, 216, 288), leaving an empty 72 px row.
        var custom = Layout(new FreeformPanel(), layout);

        Assert.Equal(0, custom[1].Y);
        Assert.Equal(CardWidth / 2, custom[1].X, tolerance: 0.5);
        Assert.Equal(62 + 72, custom[2].Y); // The row the user left empty is kept as designed.

        // Moving the others up a row closes the gap completely.
        foreach (var key in new[] { "f2", "f3", "f4" })
        {
            layout.Tiles[key].Y -= 72;
        }

        var closed = Layout(new FreeformPanel(), layout);
        Assert.Equal([0, 0, 62, 157, 197], closed.Select(r => r.Y));
    }

    [Fact]
    public void A_field_that_becomes_hidden_takes_no_room()
    {
        var panel = new FreeformPanel();
        Layout(panel, Stacked());
        var before = panel.Children[2].Bounds.Y;

        ((Border)panel.Children[1]).Height = 0; // A conditional field whose condition is not met.
        panel.InvalidateMeasure(); // The window's layout pass does this when a child changes size.
        panel.Measure(new Size(CardWidth, double.PositiveInfinity));
        panel.Arrange(new Rect(0, 0, CardWidth, panel.DesiredSize.Height));

        Assert.Equal(before - 62, panel.Children[2].Bounds.Y);
    }
}
