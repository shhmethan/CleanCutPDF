using System.Text.RegularExpressions;

namespace CleanCutPDF.Core.Naming;

/// <summary>Flexible date entry and per-field date output (1.x parse_flexible_date / format_date_for_field).</summary>
public static partial class DateFieldFormat
{
    public const string InvalidMessage =
        "Date must be a valid date such as 082026, 08-20-2026, 8-20-2026, or 2026.08.20";

    /// <summary>
    /// Accepts MMDDYY, MDDYY, MMDDYYYY, M-D-YYYY, M/D/YYYY, YYYY.M.D, YYYY-M-D and YYYY/M/D.
    /// Two-digit years follow Python: 00–68 → 2000s, 69–99 → 1900s.
    /// </summary>
    public static bool TryParse(string? raw, out DateOnly date)
    {
        date = default;
        var text = (raw ?? "").Trim();
        if (text.Length == 0)
        {
            return false;
        }

        Match m;
        if ((m = SixDigits().Match(text)).Success || (m = FiveDigits().Match(text)).Success)
        {
            return TryCreate(TwoDigitYear(m.Groups["y"].Value), m.Groups["m"].Value, m.Groups["d"].Value, out date);
        }

        if ((m = EightDigits().Match(text)).Success
            || (m = MonthFirst().Match(text)).Success
            || (m = YearFirst().Match(text)).Success)
        {
            return TryCreate(int.Parse(m.Groups["y"].Value), m.Groups["m"].Value, m.Groups["d"].Value, out date);
        }

        return false;
    }

    public static DateOnly Parse(string? raw) =>
        TryParse(raw, out var date) ? date : throw new FormatException(InvalidMessage);

    /// <summary>Formats a date in one of the field formats (M-D-YYYY pads the day, like 1.x).</summary>
    public static string Format(DateOnly date, string? format) => format switch
    {
        "MM-DD-YYYY" => $"{date.Month:00}-{date.Day:00}-{date.Year}",
        "YYYY.MM.DD" => $"{date.Year}.{date.Month:00}.{date.Day:00}",
        "MMDDYY" => $"{date.Month:00}{date.Day:00}{date.Year % 100:00}",
        _ => $"{date.Month}-{date.Day:00}-{date.Year}"
    };

    /// <summary>Re-formats user input into the field format, or throws FormatException.</summary>
    public static string FormatInput(string? raw, string? format) => Format(Parse(raw), format);

    private static int TwoDigitYear(string yy)
    {
        var value = int.Parse(yy);
        return value <= 68 ? 2000 + value : 1900 + value;
    }

    private static bool TryCreate(int year, string month, string day, out DateOnly date)
    {
        date = default;
        var m = int.Parse(month);
        var d = int.Parse(day);
        if (year is < 1 or > 9999 || m is < 1 or > 12 || d < 1 || d > DateTime.DaysInMonth(year, m))
        {
            return false;
        }

        date = new DateOnly(year, m, d);
        return true;
    }

    [GeneratedRegex(@"^(?<m>\d{2})(?<d>\d{2})(?<y>\d{2})$")]
    private static partial Regex SixDigits();

    [GeneratedRegex(@"^(?<m>[1-9])(?<d>\d{2})(?<y>\d{2})$")]
    private static partial Regex FiveDigits();

    [GeneratedRegex(@"^(?<m>\d{2})(?<d>\d{2})(?<y>\d{4})$")]
    private static partial Regex EightDigits();

    [GeneratedRegex(@"^(?<m>\d{1,2})(?<s>[-/])(?<d>\d{1,2})\k<s>(?<y>\d{4})$")]
    private static partial Regex MonthFirst();

    [GeneratedRegex(@"^(?<y>\d{4})(?<s>[./-])(?<m>\d{1,2})\k<s>(?<d>\d{1,2})$")]
    private static partial Regex YearFirst();
}
