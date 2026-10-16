using Avalonia.Controls;
using Avalonia.Data;
using Avalonia.Threading;
using CleanCutPDF.App.Controls;
using CleanCutPDF.App.ViewModels.Editor;
using CleanCutPDF.Core.Workspaces;
using Calendar = Avalonia.Controls.Calendar;

namespace CleanCutPDF.App.Tests;

/// <summary>The 📅 button on date fields: month ("01 January") and year boxes above the calendar.</summary>
public sealed class CalendarButtonTests
{
    private static TextFieldViewModel DateField(string format) =>
        new(new FieldDefinition { Key = "date_acc", Label = "Date (ACC)", Type = FieldType.Date, DateFormat = format }, []);

    [Fact]
    public void A_picked_date_is_written_in_the_field_format_and_a_typed_date_shows_in_the_calendar()
    {
        var field = DateField("YYYY.MM.DD");

        field.PickedDate = new DateTime(2026, 10, 9);
        Assert.Equal("2026.10.09", field.Text);

        field.Text = "08-20-2026";
        Assert.Equal(new DateTime(2026, 8, 20), field.PickedDate);

        field.Text = "not a date";
        Assert.Null(field.PickedDate);
        field.PickedDate = null; // Clearing from the calendar never wipes what was typed.
        Assert.Equal("not a date", field.Text);
    }

    [Fact]
    public async Task The_month_and_year_boxes_move_the_calendar_and_a_picked_day_reaches_the_field()
    {
        await HeadlessApp.RunAsync(() =>
        {
            var field = DateField("M-D-YYYY");
            field.Text = "3-15-2024";
            var button = new CalendarButton { DataContext = field };
            button.Bind(CalendarButton.SelectedDateProperty, new Binding(nameof(TextFieldViewModel.PickedDate)));
            var window = new Window { Width = 600, Height = 500, Content = button };
            window.Show();
            try
            {
                button.Flyout!.ShowAt(button);
                Dispatcher.UIThread.RunJobs();
                var panel = (StackPanel)((Flyout)button.Flyout).Content!;
                var header = (Grid)panel.Children[0];
                var month = (ComboBox)header.Children[0];
                var year = (ComboBox)header.Children[1];
                var calendar = (Calendar)panel.Children[1];

                // Opens on the field's month, with the months numbered.
                Assert.Equal("03 March", month.SelectedItem!.ToString());
                Assert.Equal("01 January", month.Items[0]!.ToString());
                Assert.Equal("12 December", month.Items[11]!.ToString());
                Assert.Equal(2024, year.SelectedItem);
                Assert.Equal(new DateTime(2024, 3, 1), calendar.DisplayDate.Date.AddDays(1 - calendar.DisplayDate.Day));

                // Jump straight to October 2026.
                month.SelectedIndex = 9;
                year.SelectedItem = 2026;
                Dispatcher.UIThread.RunJobs();
                Assert.Equal((2026, 10), (calendar.DisplayDate.Year, calendar.DisplayDate.Month));

                // The calendar's own arrows still work, and the boxes follow them.
                calendar.DisplayDate = new DateTime(2026, 11, 1);
                Dispatcher.UIThread.RunJobs();
                Assert.Equal("11 November", month.SelectedItem!.ToString());

                calendar.SelectedDate = new DateTime(2026, 11, 3);
                Dispatcher.UIThread.RunJobs();
                Assert.Equal("11-03-2026", field.Text);
                Assert.False(button.Flyout.IsOpen);
            }
            finally
            {
                window.Close();
            }
        });
    }
}
