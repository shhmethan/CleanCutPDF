using System.Globalization;
using System.Net;
using System.Text;
using System.Text.RegularExpressions;
using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.Export;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Pdf;

namespace CleanCutPDF.Core.History;

/// <summary>One exported (or renamed) file from the export history.</summary>
public sealed record HistoryEntry(
    DateTime Timestamp,
    string Workspace,
    string Client,
    string File,
    string Pages,
    string Skipped,
    string Agency,
    string Description,
    string DocumentDate,
    bool Revoked,
    string Matter,
    string DocumentType,
    string Fields,
    string Raw)
{
    public string ExportDate => Timestamp.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);

    /// <summary>A compact line of details for the Logs page.</summary>
    public string Details
    {
        get
        {
            var parts = new List<string> { $"Pages {Pages}" };
            if (Fields.Length > 0 && Fields != "None")
            {
                parts.Add(Fields.Replace("; ", " · "));
            }

            if (Skipped.Length > 0 && Skipped != "None")
            {
                parts.Add($"blank pages removed: {Skipped.Trim('[', ']')}");
            }

            if (Workspace.Length > 0)
            {
                parts.Add(Workspace);
            }

            return string.Join(" · ", parts);
        }
    }

    public string Time => Timestamp.ToString("h:mm tt", CultureInfo.CurrentCulture);
}

public enum HistorySort
{
    NewestFirst,
    OldestFirst,
    ClientAToZ,
    ClientZToA
}

public sealed record HistoryFilter(string Search = "", string Workspace = "", DateOnly? From = null, DateOnly? To = null,
    HistorySort Sort = HistorySort.NewestFirst);

/// <summary>A date heading and the clients exported that day (1.x grouped the log the same way).</summary>
public sealed record HistoryGroup(string Date, string Client, IReadOnlyList<HistoryEntry> Entries)
{
    public string Heading => $"{(Client.Length > 0 ? Client : "(no client)")} – {Date}";
}

public enum HistoryExportFormat
{
    Csv,
    Tsv,
    Txt,
    Pdf,
    Html
}

/// <summary>Reads, filters, groups, and exports the export history (1.x Logs tab).</summary>
public static partial class HistoryLog
{
    public static readonly IReadOnlyList<string> Columns =
        ["Export Date", "Client", "File", "Pages", "Skipped", "Agency", "Desc", "Date", "Revoked", "Workspace"];

    /// <summary>Parses history lines. Lines without "Client:" (folder changes, undo notes) are not entries.</summary>
    public static IReadOnlyList<HistoryEntry> Parse(IEnumerable<string> lines)
    {
        var entries = new List<HistoryEntry>();
        foreach (var line in lines)
        {
            if (!line.Contains("Client:", StringComparison.Ordinal))
            {
                continue;
            }

            var stamp = Timestamp().Match(line);
            if (!stamp.Success || !DateTime.TryParseExact(stamp.Groups[1].Value, "yyyy-MM-dd HH:mm:ss",
                    CultureInfo.InvariantCulture, DateTimeStyles.None, out var when))
            {
                continue;
            }

            string Value(string label)
            {
                var match = Regex.Match(line, $@"(?:\]|\|)\s*{Regex.Escape(label)}:\s*([^|]*)");
                return match.Success ? match.Groups[1].Value.Trim() : "";
            }

            entries.Add(new HistoryEntry(when, Value("Workspace"), Value("Client"), Value("File"), Value("Pages"),
                Value("Skipped"), Value("Agency"), Value("Desc"), Value("Date"),
                Value("Revoked").Equals("True", StringComparison.OrdinalIgnoreCase), Value("Matter"),
                Value("Document Type"), Value("Fields"), line));
        }

        return entries;
    }

    public static IReadOnlyList<HistoryEntry> Filter(IReadOnlyList<HistoryEntry> entries, HistoryFilter filter)
    {
        IEnumerable<HistoryEntry> query = entries;
        var search = filter.Search.Trim();
        if (search.Length > 0)
        {
            query = query.Where(e => e.Raw.Contains(search, StringComparison.OrdinalIgnoreCase));
        }

        var workspace = filter.Workspace.Trim();
        if (workspace.Length > 0)
        {
            query = query.Where(e => e.Workspace.Contains(workspace, StringComparison.OrdinalIgnoreCase));
        }

        if (filter.From is { } from)
        {
            query = query.Where(e => DateOnly.FromDateTime(e.Timestamp) >= from);
        }

        if (filter.To is { } to)
        {
            query = query.Where(e => DateOnly.FromDateTime(e.Timestamp) <= to);
        }

        return (filter.Sort switch
        {
            HistorySort.OldestFirst => query.OrderBy(e => e.Timestamp),
            HistorySort.ClientAToZ => query.OrderBy(e => e.Client, StringComparer.OrdinalIgnoreCase).ThenByDescending(e => e.Timestamp),
            HistorySort.ClientZToA => query.OrderByDescending(e => e.Client, StringComparer.OrdinalIgnoreCase).ThenByDescending(e => e.Timestamp),
            _ => query.OrderByDescending(e => e.Timestamp)
        }).ToList();
    }

    /// <summary>Groups consecutive entries by (date, client) in the sorted order.</summary>
    public static IReadOnlyList<HistoryGroup> Group(IReadOnlyList<HistoryEntry> sorted)
    {
        var groups = new List<HistoryGroup>();
        var index = new Dictionary<(string, string), List<HistoryEntry>>();
        foreach (var entry in sorted)
        {
            var key = (entry.ExportDate, entry.Client.ToUpperInvariant());
            if (!index.TryGetValue(key, out var list))
            {
                list = index[key] = [];
                groups.Add(new HistoryGroup(entry.ExportDate, entry.Client, list));
            }

            list.Add(entry);
        }

        return groups;
    }

    public static string[] Row(HistoryEntry e) =>
    [
        e.ExportDate, e.Client, e.File, e.Pages, e.Skipped, e.Agency, e.Description, e.DocumentDate,
        e.Revoked ? "True" : "False", e.Workspace
    ];

    /// <summary>Writes the entries in the chosen format. PDF needs the engine (built-in fonts, no extra libraries).</summary>
    public static async Task<byte[]> ExportAsync(IReadOnlyList<HistoryEntry> entries, HistoryExportFormat format,
        IPdfEngine engine, CancellationToken cancellationToken = default)
    {
        switch (format)
        {
            case HistoryExportFormat.Csv:
            case HistoryExportFormat.Tsv:
            {
                var separator = format == HistoryExportFormat.Csv ? ',' : '\t';
                var text = new StringBuilder();
                text.AppendLine(string.Join(separator, Columns));
                foreach (var entry in entries)
                {
                    var row = Row(entry);
                    row[3] = row[3].Length > 0 ? $"=\"{row[3]}\"" : ""; // keeps Excel from turning 1-2 into a date (1.x)
                    text.AppendLine(string.Join(separator, row.Select(v => format == HistoryExportFormat.Csv ? Csv(v) : v.Replace('\t', ' '))));
                }

                return new UTF8Encoding(true).GetBytes(text.ToString());
            }

            case HistoryExportFormat.Txt:
                return Encoding.UTF8.GetBytes(string.Join(Environment.NewLine, entries.Select(Line)) + Environment.NewLine);

            case HistoryExportFormat.Html:
            {
                var html = new StringBuilder("<!doctype html><html><head><meta charset=\"utf-8\"><title>CleanCutPDF export history</title>")
                    .Append("<style>body{font-family:Segoe UI,Arial,sans-serif;font-size:12px}table{border-collapse:collapse;width:100%}")
                    .Append("th,td{border:1px solid #bbb;padding:4px 6px;text-align:left}th{background:#eee}</style></head>")
                    .Append("<body onload=\"window.print()\"><h2>CleanCutPDF export history</h2><table><tr>");
                foreach (var column in Columns)
                {
                    html.Append("<th>").Append(WebUtility.HtmlEncode(column)).Append("</th>");
                }

                html.Append("</tr>");
                foreach (var entry in entries)
                {
                    html.Append("<tr>");
                    foreach (var value in Row(entry))
                    {
                        html.Append("<td>").Append(WebUtility.HtmlEncode(value)).Append("</td>");
                    }

                    html.Append("</tr>");
                }

                return Encoding.UTF8.GetBytes(html.Append("</table></body></html>").ToString());
            }

            default:
                return await engine.CreateDocumentAsync(PdfPages(entries), cancellationToken);
        }
    }

    private static string Line(HistoryEntry e) =>
        string.Join(" | ", Columns.Zip(Row(e)).Select(p => $"{p.First}: {p.Second}"));

    /// <summary>Landscape Letter pages, one entry per line (long lines are shortened).</summary>
    private static IReadOnlyList<PdfPageSpec> PdfPages(IReadOnlyList<HistoryEntry> entries)
    {
        const double width = 792, height = 612, margin = 36, lineHeight = 12;
        const int maxChars = 150;
        var pages = new List<PdfPageSpec>();
        var lines = entries.Select(Line).Select(l => l.Length > maxChars ? l[..(maxChars - 1)] + "…" : l).ToList();
        var perPage = (int)((height - 2 * margin - 24) / lineHeight);
        for (var start = 0; start < Math.Max(1, lines.Count); start += perPage)
        {
            var texts = new List<PdfTextRun>
            {
                new($"CleanCutPDF export history — {entries.Count} entr{(entries.Count == 1 ? "y" : "ies")} — page {start / perPage + 1}",
                    margin, height - margin, 11, Bold: true)
            };
            var y = height - margin - 24;
            foreach (var line in lines.Skip(start).Take(perPage))
            {
                texts.Add(new PdfTextRun(line, margin, y, 8));
                y -= lineHeight;
            }

            pages.Add(new PdfPageSpec(width, height, [], texts));
        }

        return pages;
    }

    private static string Csv(string value) =>
        value.IndexOfAny([',', '"', '\n', '\r']) >= 0 ? $"\"{value.Replace("\"", "\"\"")}\"" : value;

    [GeneratedRegex(@"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]")]
    private static partial Regex Timestamp();
}

/// <summary>Undo Last Export: moves the files to the Recycle Bin and notes it in the history.</summary>
public sealed class ExportUndo(IRecycleBin recycleBin, ExportHistory history, AppLog log, TimeProvider? clock = null)
{
    private readonly TimeProvider _clock = clock ?? TimeProvider.System;

    public sealed record UndoResult(int Recycled, IReadOnlyList<string> Problems);

    public async Task<UndoResult> UndoAsync(IReadOnlyList<string> files)
    {
        var problems = new List<string>();
        var recycled = new List<string>();
        await Task.Run(() =>
        {
            foreach (var file in files)
            {
                var reason = recycleBin.Recycle(file);
                if (reason is null)
                {
                    recycled.Add(file);
                }
                else
                {
                    problems.Add($"{Path.GetFileName(file)}: {reason}");
                }
            }

            // Remove client folders the export created that are now empty (1.x did the same).
            foreach (var folder in recycled.Select(Path.GetDirectoryName).OfType<string>().Distinct())
            {
                try
                {
                    if (Directory.Exists(folder) && !Directory.EnumerateFileSystemEntries(folder).Any())
                    {
                        Directory.Delete(folder);
                    }
                }
                catch (IOException)
                {
                    // Something else is using it; leave it.
                }
            }
        });

        var stamp = _clock.GetLocalNow().ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture);
        await history.AppendAsync(recycled.Count > 0
            ? recycled.Select(f => $"[{stamp}] Undo: Moved '{Path.GetFileName(f)}' from '{Path.GetDirectoryName(f)}' to the Recycle Bin").ToList()
            : [$"[{stamp}] Undo attempted, but no files were moved."]);
        log.Info("Undo", $"Undo last export: {recycled.Count} file(s) recycled, {problems.Count} problem(s)");
        return new UndoResult(recycled.Count, problems);
    }
}
