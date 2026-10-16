using System.Globalization;
using Avalonia;
using Avalonia.Automation;
using Avalonia.Controls;
using Avalonia.Controls.Primitives;
using Avalonia.Data;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Layout;
using CleanCutPDF.Core.Naming;
using Calendar = Avalonia.Controls.Calendar;

namespace CleanCutPDF.App.Controls;

/// <summary>A month in the calendar's month box, shown as "01 January".</summary>
public sealed record MonthChoice(int Number, string Name)
{
    public override string ToString() => $"{Number:00} {Name}";
}

/// <summary>
/// A 📅 button that opens a calendar. Above the calendar, month ("01 January")
/// and year boxes jump straight to a month; the calendar's own arrows still
/// step one month at a time. Picking a day sets <see cref="SelectedDate"/>.
/// </summary>
public sealed class CalendarButton : Button
{
    public static readonly StyledProperty<DateTime?> SelectedDateProperty =
        AvaloniaProperty.Register<CalendarButton, DateTime?>(nameof(SelectedDate), defaultBindingMode: BindingMode.TwoWay);

    private static readonly IReadOnlyList<MonthChoice> Months = Enumerable.Range(1, 12)
        .Select(m => new MonthChoice(m, CultureInfo.CurrentCulture.DateTimeFormat.GetMonthName(m)))
        .ToList();

    private readonly ComboBox _month;
    private readonly ComboBox _year;
    private readonly Calendar _calendar;
    private readonly Flyout _flyout;
    private bool _syncing;

    public CalendarButton()
    {
        Content = "📅";
        Padding = new Thickness(8, 4);
        ToolTip.SetTip(this, "Pick a date from a calendar");
        AutomationProperties.SetName(this, "Open calendar");

        _month = new ComboBox
        {
            ItemsSource = Months,
            MinWidth = 150,
            MaxDropDownHeight = 420
        };
        AutomationProperties.SetName(_month, "Month");
        _year = new ComboBox { MinWidth = 90, MaxDropDownHeight = 320 };
        AutomationProperties.SetName(_year, "Year");
        _calendar = new Calendar
        {
            SelectionMode = CalendarSelectionMode.SingleDate,
            IsTodayHighlighted = true,
            HorizontalAlignment = HorizontalAlignment.Center
        };

        var today = new Button { Content = "Today", HorizontalAlignment = HorizontalAlignment.Left };
        today.Click += (_, _) => Pick(DateTime.Today);

        var header = new Grid { ColumnDefinitions = new ColumnDefinitions("*,Auto"), ColumnSpacing = 6 };
        header.Children.Add(_month);
        Grid.SetColumn(_year, 1);
        header.Children.Add(_year);

        _flyout = new Flyout
        {
            Placement = PlacementMode.BottomEdgeAlignedLeft,
            Content = new StackPanel { Spacing = 8, Children = { header, _calendar, today } }
        };
        Flyout = _flyout;

        _month.SelectionChanged += (_, _) => JumpToChosenMonth();
        _year.SelectionChanged += (_, _) => JumpToChosenMonth();
        _calendar.DisplayDateChanged += (_, _) => ShowMonth(_calendar.DisplayDate);
        _calendar.SelectedDatesChanged += (_, _) =>
        {
            if (!_syncing && _calendar.SelectedDate is { } picked)
            {
                Pick(picked);
            }
        };
        _flyout.Opening += (_, _) => Prepare();
    }

    protected override Type StyleKeyOverride => typeof(Button);

    public DateTime? SelectedDate
    {
        get => GetValue(SelectedDateProperty);
        set => SetValue(SelectedDateProperty, value);
    }

    /// <summary>Shows the chosen date's month (or this month) each time the calendar opens.</summary>
    private void Prepare()
    {
        var shown = SelectedDate?.Date ?? DateTime.Today;
        _syncing = true;
        try
        {
            var first = Math.Min(DateTime.Today.Year - 30, shown.Year);
            var last = Math.Max(DateTime.Today.Year + 10, shown.Year);
            _year.ItemsSource = Enumerable.Range(first, last - first + 1).ToList();
            _calendar.SelectedDate = SelectedDate?.Date;
            _calendar.DisplayDate = new DateTime(shown.Year, shown.Month, 1);
        }
        finally
        {
            _syncing = false;
        }

        ShowMonth(shown);
    }

    private void ShowMonth(DateTime date)
    {
        var wasSyncing = _syncing;
        _syncing = true;
        try
        {
            _month.SelectedItem = Months[date.Month - 1];
            if (_year.ItemsSource is List<int> years && !years.Contains(date.Year))
            {
                // The arrows went past the list; widen it so the year box stays in step.
                var first = Math.Min(years[0], date.Year);
                var last = Math.Max(years[^1], date.Year);
                _year.ItemsSource = Enumerable.Range(first, last - first + 1).ToList();
            }

            _year.SelectedItem = date.Year;
        }
        finally
        {
            _syncing = wasSyncing;
        }
    }

    private void JumpToChosenMonth()
    {
        if (_syncing || _month.SelectedItem is not MonthChoice month || _year.SelectedItem is not int year)
        {
            return;
        }

        _syncing = true;
        try
        {
            _calendar.DisplayDate = new DateTime(year, month.Number, 1);
        }
        finally
        {
            _syncing = false;
        }
    }

    private void Pick(DateTime date)
    {
        SelectedDate = date.Date;
        _flyout.Hide();
    }
}

/// <summary>
/// A date box with a <see cref="CalendarButton"/> (used for the Logs filters).
/// Dates can be typed in any form the workspace date fields accept.
/// </summary>
public sealed class DateFilterBox : UserControl
{
    public static readonly StyledProperty<DateTime?> SelectedDateProperty =
        AvaloniaProperty.Register<DateFilterBox, DateTime?>(nameof(SelectedDate), defaultBindingMode: BindingMode.TwoWay);

    public static readonly StyledProperty<string?> PlaceholderTextProperty =
        AvaloniaProperty.Register<DateFilterBox, string?>(nameof(PlaceholderText));

    private readonly TextBox _text;
    private readonly CalendarButton _button;

    public DateFilterBox()
    {
        _text = new TextBox();
        _button = new CalendarButton();
        Grid.SetColumn(_button, 1);
        Content = new Grid
        {
            ColumnDefinitions = new ColumnDefinitions("*,Auto"),
            ColumnSpacing = 4,
            Children = { _text, _button }
        };

        _text.LostFocus += (_, _) => Commit();
        _text.KeyDown += (_, e) =>
        {
            if (e.Key == Key.Enter)
            {
                Commit();
                e.Handled = true;
            }
        };
        _button.PropertyChanged += (_, e) =>
        {
            if (e.Property == CalendarButton.SelectedDateProperty)
            {
                SelectedDate = _button.SelectedDate;
            }
        };
    }

    public DateTime? SelectedDate
    {
        get => GetValue(SelectedDateProperty);
        set => SetValue(SelectedDateProperty, value);
    }

    public string? PlaceholderText
    {
        get => GetValue(PlaceholderTextProperty);
        set => SetValue(PlaceholderTextProperty, value);
    }

    protected override void OnPropertyChanged(AvaloniaPropertyChangedEventArgs change)
    {
        base.OnPropertyChanged(change);
        if (change.Property == SelectedDateProperty)
        {
            var date = SelectedDate;
            _button.SelectedDate = date;
            _text.Text = date?.ToString("d", CultureInfo.CurrentCulture) ?? "";
        }
        else if (change.Property == PlaceholderTextProperty)
        {
            _text.PlaceholderText = PlaceholderText;
            AutomationProperties.SetName(_text, PlaceholderText);
        }
    }

    private void Commit()
    {
        var typed = (_text.Text ?? "").Trim();
        if (typed.Length == 0)
        {
            SelectedDate = null;
        }
        else if (DateFieldFormat.TryParse(typed, out var parsed))
        {
            SelectedDate = parsed.ToDateTime(TimeOnly.MinValue);
        }
        else if (DateTime.TryParse(typed, CultureInfo.CurrentCulture, DateTimeStyles.None, out var local))
        {
            SelectedDate = local.Date;
        }

        // Anything unreadable goes back to the last good date.
        _text.Text = SelectedDate?.ToString("d", CultureInfo.CurrentCulture) ?? "";
    }
}
