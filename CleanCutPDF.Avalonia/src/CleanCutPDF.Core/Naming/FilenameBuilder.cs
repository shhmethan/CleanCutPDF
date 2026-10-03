using System.Text.RegularExpressions;
using CleanCutPDF.Core.Workspaces;

namespace CleanCutPDF.Core.Naming;

/// <summary>Raw values entered for one Part. Booleans are stored as "true"/"false".</summary>
public sealed class PartValues : Dictionary<string, string>
{
    public PartValues() : base(StringComparer.Ordinal)
    {
    }

    public PartValues(IDictionary<string, string> values) : base(values, StringComparer.Ordinal)
    {
    }

    public string Get(string key) => TryGetValue(key, out var value) ? value : "";
}

public static class FieldRules
{
    /// <summary>Conditional visibility, e.g. Check Number only when Payment Method = CK.</summary>
    public static bool IsVisible(FieldDefinition field, PartValues values, ResolvedWorkspace workspace)
    {
        if (field.Condition is not { } condition)
        {
            return true;
        }

        var controller = workspace.Field(condition.Field);
        if (controller is null)
        {
            return false;
        }

        var actual = values.Get(condition.Field);
        if (controller.IsBoolean)
        {
            actual = FieldDefinition.IsTrue(actual) ? "True" : "False";
        }

        return string.Equals(actual.Trim(), condition.EqualsValue.Trim(), StringComparison.OrdinalIgnoreCase);
    }

    /// <summary>The value a field starts with (default, or today's date for auto-today Date fields).</summary>
    public static string InitialValue(FieldDefinition field, DateOnly today)
    {
        if (field.IsBoolean)
        {
            return FieldDefinition.IsTrue(field.Default) ? "true" : "false";
        }

        if (field.Type == FieldType.Date && field.AutoToday && string.IsNullOrWhiteSpace(field.Default))
        {
            return DateFieldFormat.Format(today, field.DateFormat);
        }

        return field.Default;
    }
}

/// <summary>Builds the filename tokens and the final filename (1.x get_workspace_export_values / _format_workspace_filename).</summary>
public static partial class FilenameBuilder
{
    private static readonly HashSet<string> ReservedNames =
    [
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    ];

    /// <summary>
    /// Converts raw Part values into filename tokens. Throws FormatException
    /// (with a user-facing message) for an invalid date or currency.
    /// </summary>
    public static Dictionary<string, string> BuildTokens(ResolvedWorkspace workspace, string clientName, PartValues values)
    {
        var tokens = new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["client"] = clientName,
            ["workspace"] = workspace.Name
        };

        foreach (var field in workspace.Fields)
        {
            if (!FieldRules.IsVisible(field, values, workspace))
            {
                tokens[field.Key] = "";
                continue;
            }

            var raw = values.Get(field.Key);
            string processed;
            if (field.IsBoolean)
            {
                var on = FieldDefinition.IsTrue(raw);
                processed = !on ? "" : field.Key == "revoked" ? "Revoked" : field.Label;
            }
            else
            {
                processed = raw.Trim();
                if (field.Key == "agency")
                {
                    processed = AgencyCodes.Expand(processed);
                }

                if (field.Key == "description" && processed.Length > 0)
                {
                    processed = InvoiceShortcut().Replace(processed, "Invoice");
                }

                if (processed.Length > 0)
                {
                    processed = field.Type switch
                    {
                        FieldType.Currency => CurrencyFormat.Format(processed),
                        FieldType.Date => DateFieldFormat.FormatInput(processed, field.DateFormat),
                        _ => processed
                    };
                }

                if (field.TitleCase && processed.Length > 0)
                {
                    processed = NameCasing.TitleCase(processed);
                }
            }

            tokens[field.Key] = processed;
        }

        foreach (var key in new[] { "revoked", "agency", "description", "date", "matter_number", "document_type" })
        {
            tokens.TryAdd(key, "");
        }

        tokens["agency_description"] = string.Join(' ',
            new[] { tokens["agency"], tokens["description"] }.Where(p => p.Length > 0)).Trim();
        return tokens;
    }

    /// <summary>Renders a template such as "{client}_{revoked}_{agency_description}_{date}" into a safe filename (no extension).</summary>
    public static string Render(string template, IReadOnlyDictionary<string, string> tokens)
    {
        var name = Token().Replace(template, match =>
        {
            var key = match.Groups["key"].Value;
            var value = tokens.TryGetValue(key, out var v) ? v : "";
            // Check Number may follow a payment method inside one block ("CK 1234").
            return key == "check_number" && value.Trim().Length > 0 ? " " + value.Trim() : value;
        });
        name = name.Replace("{{", "{").Replace("}}", "}");
        return Sanitize(name);
    }

    public static string Sanitize(string name)
    {
        name = IllegalCharacters().Replace(name, "_");
        name = SpaceBeforeUnderscore().Replace(name, "_");
        name = RepeatedUnderscores().Replace(name, "_");
        name = RepeatedSpaces().Replace(name, " ");
        name = name.Trim(' ', '_', '-').TrimEnd('.', ' ');
        if (ReservedNames.Contains(name.ToUpperInvariant()))
        {
            name = "_" + name;
        }

        return name.Length == 0 ? "Document" : name;
    }

    [GeneratedRegex(@"(?<!\{)\{(?<key>[A-Za-z0-9_]+)\}(?!\})")]
    private static partial Regex Token();

    [GeneratedRegex(@"\binv\b", RegexOptions.IgnoreCase)]
    private static partial Regex InvoiceShortcut();

    [GeneratedRegex("[<>:\"/\\\\|?*\\x00-\\x1F]")]
    private static partial Regex IllegalCharacters();

    [GeneratedRegex(@"\s+_")]
    private static partial Regex SpaceBeforeUnderscore();

    [GeneratedRegex(@"_{2,}")]
    private static partial Regex RepeatedUnderscores();

    [GeneratedRegex(@"\s{2,}")]
    private static partial Regex RepeatedSpaces();
}
