using System.Text.RegularExpressions;
using CleanCutPDF.Core.History;
using CleanCutPDF.Core.Workspaces;

namespace CleanCutPDF.Core.Naming;

public enum RecognitionSource
{
    /// <summary>The file name is in the export history, which recorded the values.</summary>
    ExportLog,

    /// <summary>The values were read back out of the name using a workspace's filename format.</summary>
    FilenameFormat
}

/// <summary>Field values recovered from an exported file's name (raw values, as the form stores them).</summary>
public sealed record RecognizedName(
    string Workspace,
    string Client,
    IReadOnlyDictionary<string, string> Values,
    RecognitionSource Source,
    DateTime? ExportedAt = null);

/// <summary>
/// Fills a Part back in from a file CleanCutPDF exported earlier, so a mistake
/// can be fixed in Rename Only. The export history is tried first (exact file
/// name); otherwise the name is matched against the workspaces' filename formats,
/// and only a reading that rebuilds exactly the same name is used.
/// </summary>
public static partial class FilenameRecognizer
{
    private const int SearchBudget = 50_000;

    public static RecognizedName? Recognize(string fileName, WorkspaceCatalog catalog, IReadOnlyList<HistoryEntry> history,
        IReadOnlyCollection<string> knownClients, string? preferredWorkspace = null) =>
        FromHistory(fileName, catalog, history) ?? FromFilename(fileName, catalog, knownClients, preferredWorkspace);

    // ───── Export history ─────

    public static RecognizedName? FromHistory(string fileName, WorkspaceCatalog catalog, IReadOnlyList<HistoryEntry> history)
    {
        var name = Path.GetFileName(fileName);
        var entry = history
            .Where(e => string.Equals(e.File, name, StringComparison.OrdinalIgnoreCase))
            .Where(e => catalog.WorkspaceNames.Contains(e.Workspace))
            .MaxBy(e => e.Timestamp);
        if (entry is null)
        {
            return null;
        }

        var workspace = catalog.Resolve(entry.Workspace);
        var logged = ParseFields(entry.Fields, workspace);
        if (logged.Count == 0)
        {
            // Older lines have no Fields list; use the fixed columns they do have.
            AddIfPresent(logged, workspace, "agency", entry.Agency);
            AddIfPresent(logged, workspace, "description", entry.Description);
            AddIfPresent(logged, workspace, "date", entry.DocumentDate == "None" ? "" : entry.DocumentDate);
            AddIfPresent(logged, workspace, "matter_number", entry.Matter);
            AddIfPresent(logged, workspace, "document_type", entry.DocumentType);
            if (entry.Revoked && workspace.Field("revoked") is not null)
            {
                logged["revoked"] = "Revoked";
            }
        }

        return new RecognizedName(workspace.Name, entry.Client, ToRawValues(workspace, logged), RecognitionSource.ExportLog,
            entry.Timestamp);
    }

    /// <summary>"Label=value; Label=value" from a history line, keyed by field key. Values may contain "; ".</summary>
    internal static Dictionary<string, string> ParseFields(string fields, ResolvedWorkspace workspace)
    {
        var result = new Dictionary<string, string>(StringComparer.Ordinal);
        if (string.IsNullOrWhiteSpace(fields) || fields.Trim() == "None")
        {
            return result;
        }

        string? currentKey = null;
        foreach (var piece in fields.Split("; "))
        {
            var equals = piece.IndexOf('=');
            var field = equals > 0
                ? workspace.Fields.FirstOrDefault(f => string.Equals(f.Label, piece[..equals].Trim(), StringComparison.OrdinalIgnoreCase))
                : null;
            if (field is not null)
            {
                currentKey = field.Key;
                result[currentKey] = piece[(equals + 1)..];
            }
            else if (currentKey is not null)
            {
                result[currentKey] += "; " + piece; // Part of the previous value.
            }
        }

        return result;
    }

    private static void AddIfPresent(Dictionary<string, string> values, ResolvedWorkspace workspace, string key, string value)
    {
        if (value.Length > 0 && workspace.Field(key) is not null)
        {
            values[key] = value;
        }
    }

    /// <summary>Filename tokens (processed values) back to what the form stores.</summary>
    private static Dictionary<string, string> ToRawValues(ResolvedWorkspace workspace, IReadOnlyDictionary<string, string> tokens)
    {
        var values = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var field in workspace.Fields)
        {
            var token = tokens.TryGetValue(field.Key, out var t) ? t.Trim() : "";
            values[field.Key] = field.IsBoolean ? (token.Length > 0 ? "true" : "false") : token;
        }

        return values;
    }

    // ───── Filename format ─────

    public static RecognizedName? FromFilename(string fileName, WorkspaceCatalog catalog, IReadOnlyCollection<string> knownClients,
        string? preferredWorkspace = null)
    {
        var baseName = Path.GetFileNameWithoutExtension(fileName).Trim();
        if (baseName.Length == 0)
        {
            return null;
        }

        var known = new HashSet<string>(knownClients, StringComparer.OrdinalIgnoreCase);
        // name_2.pdf is how a second export of the same name is saved; try the name without it first.
        var names = new List<string>();
        if (UniqueSuffix().Match(baseName) is { Success: true } suffix)
        {
            names.Add(baseName[..suffix.Index]);
        }

        names.Add(baseName);

        var order = catalog.WorkspaceNames.OrderBy(n => n == preferredWorkspace ? 0 : 1).ToList();
        foreach (var name in names)
        {
            Candidate? best = null;
            foreach (var workspaceName in order)
            {
                var candidate = BestReading(name, catalog.Resolve(workspaceName), known);
                if (candidate is not null && (best is null || candidate.Score > best.Score))
                {
                    best = candidate;
                }
            }

            if (best is not null)
            {
                return new RecognizedName(best.Workspace, best.Client, best.Values, RecognitionSource.FilenameFormat);
            }
        }

        return null;
    }

    private sealed record Candidate(string Workspace, string Client, Dictionary<string, string> Values, double Score);

    private abstract record Segment;

    private sealed record Literal(string Text) : Segment;

    private sealed record TokenSegment(string Key) : Segment;

    private static Candidate? BestReading(string baseName, ResolvedWorkspace workspace, HashSet<string> knownClients)
    {
        var segments = Segments(workspace.FilenameTemplate);
        if (!segments.OfType<TokenSegment>().Any())
        {
            return null;
        }

        Candidate? best = null;
        var budget = SearchBudget;
        var tokens = new Dictionary<string, string>(StringComparer.Ordinal);

        void Walk(int index, int position)
        {
            if (--budget < 0)
            {
                return;
            }

            if (index == segments.Count)
            {
                if (position == baseName.Length)
                {
                    foreach (var values in Readings(workspace, tokens))
                    {
                        Consider(values);
                    }
                }

                return;
            }

            switch (segments[index])
            {
                case Literal literal:
                    if (string.CompareOrdinal(baseName, position, literal.Text, 0, literal.Text.Length) == 0)
                    {
                        Walk(index + 1, position + literal.Text.Length);
                    }

                    // Separators beside an empty token (or at either end) disappear when the name is tidied.
                    var afterEmpty = index == 0 || segments[index - 1] is TokenSegment previous
                        && tokens.TryGetValue(previous.Key, out var text) && text.Length == 0;
                    if (IsSeparators(literal.Text) && (afterEmpty || position == baseName.Length))
                    {
                        Walk(index + 1, position);
                    }

                    break;
                case TokenSegment token:
                    if (tokens.TryGetValue(token.Key, out var earlier))
                    {
                        // The same token twice must have the same text both times.
                        if (string.CompareOrdinal(baseName, position, earlier, 0, earlier.Length) == 0)
                        {
                            Walk(index + 1, position + earlier.Length);
                        }

                        break;
                    }

                    var next = index + 1 < segments.Count ? segments[index + 1] : null;
                    foreach (var end in Ends(baseName, position, token.Key, workspace, next))
                    {
                        if (budget < 0)
                        {
                            break;
                        }

                        tokens[token.Key] = baseName[position..end];
                        Walk(index + 1, end);
                    }

                    tokens.Remove(token.Key);
                    break;
            }
        }

        void Consider(Dictionary<string, string> values)
        {
            var client = values.TryGetValue("client", out var c) ? c : "";
            values.Remove("client");
            try
            {
                var rebuilt = FilenameBuilder.Render(workspace.FilenameTemplate,
                    FilenameBuilder.BuildTokens(workspace, client, new PartValues(values)));
                if (rebuilt != baseName)
                {
                    return;
                }
            }
            catch (FormatException)
            {
                return; // Not a valid date or amount for that field.
            }

            // On/off fields only match their own label, so a match is evidence rather than a guess.
            var switches = workspace.Fields.Count(f => f.IsBoolean && values.TryGetValue(f.Key, out var v) && v == "true");
            var filled = workspace.Fields.Count(f => !f.IsBoolean && values.TryGetValue(f.Key, out var v) && v.Length > 0);
            var typed = workspace.Fields.Count(f => f.Type is FieldType.Date or FieldType.Currency
                                                    && values.TryGetValue(f.Key, out var v) && v.Length > 0);
            var isKnown = client.Length > 0 && knownClients.Contains(client);
            // Only trust a reading that something confirms: a client from the history, or a date/amount plus more.
            if (!isKnown && (typed == 0 || filled + (client.Length > 0 ? 1 : 0) < 2))
            {
                return;
            }

            // Prefer known clients, then the reading that assumes the fewest filled-in fields.
            // A known agency at the start of {agency_description} counts in favour (IRS, FTB…).
            var agency = values.TryGetValue("agency", out var a) && a.Length > 0 ? 20 : 0;
            var score = (isKnown ? 1000 : 0) + typed * 50 + agency + switches * 20 - filled * 10 - (client.Length > 0 ? 0 : 5);
            if (best is null || score > best.Score)
            {
                best = new Candidate(workspace.Name, client, values, score);
            }
        }

        Walk(0, 0);
        return best;
    }

    /// <summary>
    /// Where a token starting at <paramref name="start"/> may end. Dates and amounts must read as one,
    /// on/off fields can only be their label, and free text stops where the next separator text appears.
    /// </summary>
    private static IEnumerable<int> Ends(string name, int start, string key, ResolvedWorkspace workspace, Segment? next)
    {
        yield return start; // Empty.
        var field = workspace.Field(key);
        if (key == "workspace" || field is { IsBoolean: true })
        {
            var words = key == "workspace" ? new[] { workspace.Name } : new[] { field!.Label, "Revoked" };
            foreach (var word in words.Distinct())
            {
                if (word.Length > 0 && string.CompareOrdinal(name, start, word, 0, word.Length) == 0)
                {
                    yield return start + word.Length;
                }
            }

            yield break;
        }

        if (field?.Type is FieldType.Date or FieldType.Currency)
        {
            for (var end = start + 1; end <= Math.Min(name.Length, start + 24); end++)
            {
                var text = name[start..end];
                if (field.Type == FieldType.Date ? DateFieldFormat.TryParse(text, out _) : CurrencyFormat.TryFormat(text, out _))
                {
                    yield return end;
                }
            }

            yield break;
        }

        if (start >= name.Length)
        {
            yield break;
        }

        if (next is Literal literal)
        {
            for (var at = name.IndexOf(literal.Text, start + 1, StringComparison.Ordinal);
                 at >= 0;
                 at = at + 1 < name.Length ? name.IndexOf(literal.Text, at + 1, StringComparison.Ordinal) : -1)
            {
                yield return at;
            }

            if (name.Length > start)
            {
                yield return name.Length; // The rest of the separators were trimmed away.
            }

            yield break;
        }

        for (var end = start + 1; end <= name.Length; end++)
        {
            yield return end;
        }
    }

    /// <summary>Raw values for a matched set of tokens (several when "agency_description" can be split more than one way).</summary>
    private static IEnumerable<Dictionary<string, string>> Readings(ResolvedWorkspace workspace, Dictionary<string, string> tokens)
    {
        var processed = new Dictionary<string, string>(tokens, StringComparer.Ordinal);
        processed.Remove("workspace");
        var client = processed.Remove("client", out var c) ? c.Trim() : "";

        var splits = new List<(string Agency, string Description)?> { null };
        if (processed.Remove("agency_description", out var combined))
        {
            splits.Clear();
            combined = combined.Trim();
            splits.Add(("", combined));
            if (workspace.Field("agency") is { } agency)
            {
                var agencies = agency.Options.Append("IRS").Append("FTB").Append("EDD").Append("CDTFA").Append("BOE")
                    .Select(AgencyCodes.Expand)
                    .Where(a => a.Length > 0)
                    .Distinct(StringComparer.Ordinal);
                foreach (var name in agencies)
                {
                    if (combined == name)
                    {
                        splits.Add((name, ""));
                    }
                    else if (combined.StartsWith(name + " ", StringComparison.Ordinal))
                    {
                        splits.Add((name, combined[(name.Length + 1)..]));
                    }
                }
            }
        }

        foreach (var split in splits)
        {
            var set = new Dictionary<string, string>(processed, StringComparer.Ordinal);
            if (split is { } s)
            {
                if (set.TryGetValue("agency", out var a) && a.Trim() != s.Agency || set.TryGetValue("description", out var d) && d.Trim() != s.Description)
                {
                    continue; // The template also has {agency} or {description} on its own, and they disagree.
                }

                set["agency"] = s.Agency;
                set["description"] = s.Description;
            }

            var values = ToRawValues(workspace, set);
            values["client"] = client;
            yield return values;
        }
    }

    private static List<Segment> Segments(string template)
    {
        var segments = new List<Segment>();
        var last = 0;
        foreach (Match match in Token().Matches(template))
        {
            if (match.Index > last)
            {
                segments.Add(new Literal(Unescape(template[last..match.Index])));
            }

            segments.Add(new TokenSegment(match.Groups["key"].Value));
            last = match.Index + match.Length;
        }

        if (last < template.Length)
        {
            segments.Add(new Literal(Unescape(template[last..])));
        }

        return segments.Where(s => s is not Literal { Text.Length: 0 }).ToList();
    }

    private static string Unescape(string text) => text.Replace("{{", "{").Replace("}}", "}");

    private static bool IsSeparators(string text) => text.Length > 0 && text.All(ch => ch is ' ' or '_' or '-');

    [GeneratedRegex(@"(?<!\{)\{(?<key>[A-Za-z0-9_]+)\}(?!\})")]
    private static partial Regex Token();

    [GeneratedRegex(@"_\d+$")]
    private static partial Regex UniqueSuffix();
}
