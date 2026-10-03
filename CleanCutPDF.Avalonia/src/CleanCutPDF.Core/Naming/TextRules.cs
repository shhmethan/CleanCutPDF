using System.Globalization;
using System.Text.RegularExpressions;

namespace CleanCutPDF.Core.Naming;

public static class CurrencyFormat
{
    public const string InvalidMessage = "Currency must be a number such as 134.06";

    /// <summary>"1234.5", "$1,234.50", "1234.5 USD" → "$1,234.50" (banker's rounding, like Python Decimal).</summary>
    public static string Format(string? raw)
    {
        var text = (raw ?? "").Trim();
        if (text.Length == 0)
        {
            return "";
        }

        var cleaned = text.ToUpperInvariant().Replace("USD", "").Replace("$", "").Replace(",", "").Trim();
        if (!decimal.TryParse(cleaned, NumberStyles.Float, CultureInfo.InvariantCulture, out var amount))
        {
            throw new FormatException(InvalidMessage);
        }

        amount = Math.Round(amount, 2, MidpointRounding.ToEven);
        return "$" + amount.ToString("#,##0.00", CultureInfo.InvariantCulture);
    }

    public static bool TryFormat(string? raw, out string formatted)
    {
        try
        {
            formatted = Format(raw);
            return true;
        }
        catch (FormatException)
        {
            formatted = raw ?? "";
            return false;
        }
    }
}

public static partial class NameCasing
{
    private static readonly HashSet<string> Acronyms =
        ["POA", "LLC", "INC", "LP", "LLP", "PLC", "DBA", "CPA", "PC", "PLLC", "LLLP"];

    /// <summary>
    /// Smart title case from 1.x: keeps acronyms upper case, handles hyphenated
    /// names, Mc and O' prefixes, and leaves words that already contain capitals
    /// after the first letter alone (so "McDonald" or "JARB" stay as typed).
    ///
    /// Difference from 1.x: the automatic "Mac" rule is not applied, because it
    /// turned "Machado" into "MacHado" and "Macy" into "MacY". Typing "MacDonald"
    /// still keeps that capitalization.
    /// </summary>
    public static string TitleCase(string? text)
    {
        if (string.IsNullOrWhiteSpace(text))
        {
            return "";
        }

        return string.Join(' ', Words().Matches(text).Select(m => CapitalizeWord(m.Value)));
    }

    private static string CapitalizeWord(string word)
    {
        if (word.Length == 0)
        {
            return "";
        }

        if (Acronyms.Contains(word.ToUpperInvariant()))
        {
            return word.ToUpperInvariant();
        }

        if (word.Contains('-'))
        {
            return string.Join('-', word.Split('-').Select(CapitalizeWord));
        }

        var lower = word.ToLowerInvariant();
        if (lower.StartsWith("mc", StringComparison.Ordinal) && word.Length > 2)
        {
            return "Mc" + char.ToUpperInvariant(word[2]) + word[3..].ToLowerInvariant();
        }

        if (lower.StartsWith("o'", StringComparison.Ordinal) && word.Length > 2)
        {
            return "O'" + char.ToUpperInvariant(word[2]) + word[3..].ToLowerInvariant();
        }

        if (word[1..].Any(char.IsUpper))
        {
            return word; // Preserve intentional capitalization.
        }

        return char.ToUpperInvariant(word[0]) + word[1..].ToLowerInvariant();
    }

    [GeneratedRegex(@"\S+")]
    private static partial Regex Words();
}

public static class AgencyCodes
{
    private static readonly Dictionary<string, string> Codes = new(StringComparer.OrdinalIgnoreCase)
    {
        ["i"] = "IRS",
        ["f"] = "FTB",
        ["e"] = "EDD",
        ["c"] = "CDTFA",
        ["b"] = "BOE"
    };

    /// <summary>I/F/E/C/B expand to the agency name; anything else is upper-cased.</summary>
    public static string Expand(string? code)
    {
        var text = (code ?? "").Trim();
        return Codes.TryGetValue(text, out var name) ? name : text.ToUpperInvariant();
    }
}
