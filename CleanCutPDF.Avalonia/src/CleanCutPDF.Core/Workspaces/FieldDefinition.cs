using System.Text.Json.Serialization;

namespace CleanCutPDF.Core.Workspaces;

[JsonConverter(typeof(JsonStringEnumConverter<FieldType>))]
public enum FieldType
{
    Text,
    Number,
    Currency,
    Date,
    Choice,
    Checkbox,
    Toggle
}

public sealed class FieldCondition
{
    /// <summary>Key of the field that controls visibility.</summary>
    public string Field { get; set; } = "";

    /// <summary>Show the field when the controller equals this (case-insensitive; booleans compare as True/False).</summary>
    public string EqualsValue { get; set; } = "";
}

/// <summary>A reusable field from the field library (same options as 1.x custom fields).</summary>
public sealed class FieldDefinition
{
    public const string DefaultDateFormat = "M-D-YYYY";
    public static readonly IReadOnlyList<string> DateFormats = ["M-D-YYYY", "MM-DD-YYYY", "YYYY.MM.DD", "MMDDYY"];

    public string Key { get; set; } = "";
    public string Label { get; set; } = "";
    public FieldType Type { get; set; } = FieldType.Text;
    public string Placeholder { get; set; } = "";

    /// <summary>Default value. For checkbox/toggle fields, "true" or "false".</summary>
    public string Default { get; set; } = "";

    public bool Required { get; set; }

    /// <summary>A value typed in one Part carries forward to the following Parts.</summary>
    public bool Autofill { get; set; }

    public bool TitleCase { get; set; }
    public string DateFormat { get; set; } = DefaultDateFormat;

    /// <summary>Date fields start with today's date when blank.</summary>
    public bool AutoToday { get; set; }

    public List<string> Options { get; set; } = [];
    public FieldCondition? Condition { get; set; }

    /// <summary>Optional #RRGGBB accent color.</summary>
    public string Color { get; set; } = "";

    public string? Tooltip { get; set; }

    /// <summary>"header" places a toggle/checkbox in the Part header.</summary>
    public string? Placement { get; set; }

    /// <summary>Built-in field shipped with the app.</summary>
    public bool System { get; set; }

    [JsonIgnore]
    public bool IsBoolean => Type is FieldType.Checkbox or FieldType.Toggle;

    [JsonIgnore]
    public bool IsHeaderField => IsBoolean && Placement == "header";

    public FieldDefinition Clone()
    {
        var copy = (FieldDefinition)MemberwiseClone();
        copy.Options = [.. Options];
        copy.Condition = Condition is null ? null : new FieldCondition { Field = Condition.Field, EqualsValue = Condition.EqualsValue };
        return copy;
    }

    public static bool IsTrue(string? value) =>
        value?.Trim().ToLowerInvariant() is "true" or "1" or "yes" or "on" or "checked";
}

/// <summary>Per-workspace adjustments to a library field.</summary>
public sealed class FieldOverride
{
    public string? Default { get; set; }
    public bool? Autofill { get; set; }
    public bool? Required { get; set; }
    public string? Label { get; set; }
}
