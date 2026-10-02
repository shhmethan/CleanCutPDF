namespace CleanCutPDF.Core.Updates;

/// <summary>
/// Semantic-style version ("v2.0.0-alpha.1"). Like the 1.x parse_version it is
/// forgiving: a leading "v" is ignored and non-numeric suffixes in a part are
/// dropped. A pre-release sorts before the matching release.
/// </summary>
public sealed class AppVersion : IComparable<AppVersion>, IEquatable<AppVersion>
{
    private AppVersion(int[] numbers, string[] preRelease, string text)
    {
        Numbers = numbers;
        PreRelease = preRelease;
        Text = text;
    }

    public IReadOnlyList<int> Numbers { get; }
    public IReadOnlyList<string> PreRelease { get; }
    public string Text { get; }
    public bool IsPreRelease => PreRelease.Count > 0;

    public static AppVersion Parse(string? value)
    {
        var text = (value ?? "").Trim();
        var core = text.TrimStart('v', 'V').Split('+')[0];
        var dash = core.IndexOf('-');
        var pre = dash >= 0 ? core[(dash + 1)..] : "";
        if (dash >= 0)
        {
            core = core[..dash];
        }

        var numbers = core.Split('.')
            .Select(part => new string(part.TakeWhile(char.IsDigit).ToArray()))
            .Select(digits => int.TryParse(digits, out var n) ? n : 0)
            .ToList();
        while (numbers.Count < 3)
        {
            numbers.Add(0);
        }

        var preParts = pre.Length == 0 ? [] : pre.Split('.', StringSplitOptions.RemoveEmptyEntries);
        return new AppVersion(numbers.ToArray(), preParts, text);
    }

    public int CompareTo(AppVersion? other)
    {
        if (other is null)
        {
            return 1;
        }

        for (var i = 0; i < Math.Max(Numbers.Count, other.Numbers.Count); i++)
        {
            var a = i < Numbers.Count ? Numbers[i] : 0;
            var b = i < other.Numbers.Count ? other.Numbers[i] : 0;
            if (a != b)
            {
                return a.CompareTo(b);
            }
        }

        // 2.0.0-alpha < 2.0.0
        if (IsPreRelease != other.IsPreRelease)
        {
            return IsPreRelease ? -1 : 1;
        }

        for (var i = 0; i < Math.Min(PreRelease.Count, other.PreRelease.Count); i++)
        {
            var x = PreRelease[i];
            var y = other.PreRelease[i];
            var xNumeric = int.TryParse(x, out var xn);
            var yNumeric = int.TryParse(y, out var yn);
            var result = xNumeric && yNumeric ? xn.CompareTo(yn)
                : xNumeric ? -1
                : yNumeric ? 1
                : string.CompareOrdinal(x, y);
            if (result != 0)
            {
                return result;
            }
        }

        return PreRelease.Count.CompareTo(other.PreRelease.Count);
    }

    public bool Equals(AppVersion? other) => CompareTo(other) == 0;
    public override bool Equals(object? obj) => obj is AppVersion other && Equals(other);
    public override int GetHashCode() => HashCode.Combine(Numbers[0], Numbers[1], Numbers[2], PreRelease.Count);
    public override string ToString() => Text;

    public static bool operator >(AppVersion a, AppVersion b) => a.CompareTo(b) > 0;
    public static bool operator <(AppVersion a, AppVersion b) => a.CompareTo(b) < 0;
}
