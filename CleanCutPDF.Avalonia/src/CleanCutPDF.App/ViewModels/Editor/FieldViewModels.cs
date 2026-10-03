using Avalonia.Media;
using CleanCutPDF.Core.Naming;
using CleanCutPDF.Core.Workspaces;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace CleanCutPDF.App.ViewModels.Editor;

/// <summary>Base for one field in one Part. Value is the raw stored value ("true"/"false" for booleans).</summary>
public abstract partial class FieldViewModel : ObservableObject
{
    private string _value = "";

    protected FieldViewModel(FieldDefinition definition, IReadOnlyList<string> notes)
    {
        Definition = definition;
        Notes = notes;
        Accent = TryParseColor(definition.Color);
    }

    public FieldDefinition Definition { get; }
    public string Key => Definition.Key;

    /// <summary>Workspace reminders shown directly under this field's title.</summary>
    public IReadOnlyList<string> Notes { get; }

    public bool HasNotes => Notes.Count > 0;

    public string DisplayLabel =>
        Definition.Label
        + (Definition.Type == FieldType.Date ? $" ({Definition.DateFormat})" : "")
        + (Definition.Required ? " *" : "");

    public IBrush? Accent { get; }
    public bool HasAccent => Accent is not null;
    public string? Tooltip => Definition.Tooltip;
    public bool HasTooltip => !string.IsNullOrWhiteSpace(Definition.Tooltip);

    [ObservableProperty]
    public partial bool IsVisible { get; set; } = true;

    /// <summary>Raised with (old, new) whenever the value changes, from the UI or programmatically.</summary>
    public event Action<FieldViewModel, string, string>? ValueChanged;

    public string Value
    {
        get => _value;
        set
        {
            value ??= "";
            if (_value == value)
            {
                return;
            }

            var old = _value;
            _value = value;
            OnValueChanged();
            OnPropertyChanged();
            ValueChanged?.Invoke(this, old, value);
        }
    }

    /// <summary>Updates the editing controls after Value changed.</summary>
    protected abstract void OnValueChanged();

    public static FieldViewModel Create(FieldDefinition definition, IReadOnlyList<string> notes) => definition.Type switch
    {
        FieldType.Checkbox or FieldType.Toggle => new BooleanFieldViewModel(definition, notes),
        FieldType.Choice => new ChoiceFieldViewModel(definition, notes),
        _ => new TextFieldViewModel(definition, notes)
    };

    private static IBrush? TryParseColor(string? color) =>
        !string.IsNullOrWhiteSpace(color) && Color.TryParse(color, out var parsed) ? new SolidColorBrush(parsed) : null;
}

/// <summary>Text, number, currency, and date fields.</summary>
public sealed partial class TextFieldViewModel(FieldDefinition definition, IReadOnlyList<string> notes)
    : FieldViewModel(definition, notes)
{
    public string Placeholder => Definition.Placeholder;
    public bool IsDate => Definition.Type == FieldType.Date;

    public string Text
    {
        get => Value;
        set => Value = value;
    }

    protected override void OnValueChanged() => OnPropertyChanged(nameof(Text));

    /// <summary>The Today button (uses this field's date format).</summary>
    [RelayCommand]
    private void Today() => Value = DateFieldFormat.Format(DateOnly.FromDateTime(DateTime.Today), Definition.DateFormat);

    /// <summary>Currency fields tidy themselves when the user leaves them (1.x normalize_currency).</summary>
    public void Normalize()
    {
        if (Definition.Type == FieldType.Currency && CurrencyFormat.TryFormat(Value, out var formatted))
        {
            Value = formatted; // Invalid input is left as typed so export can explain the problem.
        }
    }
}

/// <summary>Checkbox and toggle fields.</summary>
public sealed partial class BooleanFieldViewModel(FieldDefinition definition, IReadOnlyList<string> notes)
    : FieldViewModel(definition, notes)
{
    public bool IsToggle => Definition.Type == FieldType.Toggle;

    public bool IsChecked
    {
        get => FieldDefinition.IsTrue(Value);
        set => Value = value ? "true" : "false";
    }

    protected override void OnValueChanged() => OnPropertyChanged(nameof(IsChecked));
}

/// <summary>Dropdown with "Select..." and an optional "Other" free-text entry.</summary>
public sealed partial class ChoiceFieldViewModel : FieldViewModel
{
    public const string Placeholder = "Select...";
    private readonly string? _otherOption;
    private bool _syncing;

    public ChoiceFieldViewModel(FieldDefinition definition, IReadOnlyList<string> notes) : base(definition, notes)
    {
        var options = definition.Options.Where(o => !string.IsNullOrWhiteSpace(o)).ToList();
        if (options.Count == 0)
        {
            options.Add("Other");
        }

        _otherOption = options.FirstOrDefault(o => string.Equals(o, "Other", StringComparison.OrdinalIgnoreCase));
        Options = [Placeholder, .. options];
        SelectedOption = Placeholder;
    }

    public IReadOnlyList<string> Options { get; }

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(ShowOther))]
    public partial string? SelectedOption { get; set; }

    [ObservableProperty]
    public partial string OtherText { get; set; } = "";

    public bool ShowOther => _otherOption is not null && SelectedOption == _otherOption;

    partial void OnSelectedOptionChanged(string? value)
    {
        if (_syncing)
        {
            return;
        }

        Value = value is null || value == Placeholder ? "" : value == _otherOption ? OtherText : value;
    }

    partial void OnOtherTextChanged(string value)
    {
        if (!_syncing && ShowOther)
        {
            Value = value;
        }
    }

    protected override void OnValueChanged()
    {
        if (_syncing)
        {
            return;
        }

        _syncing = true;
        try
        {
            if (Value.Length == 0)
            {
                // "Other" with an empty box stays on Other while the user types.
                if (!ShowOther)
                {
                    SelectedOption = Placeholder;
                }
            }
            else if (Options.Skip(1).Contains(Value) && Value != _otherOption)
            {
                SelectedOption = Value;
            }
            else if (_otherOption is not null)
            {
                SelectedOption = _otherOption;
                OtherText = Value;
            }
        }
        finally
        {
            _syncing = false;
        }
    }
}
