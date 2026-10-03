using System.Globalization;
using System.Text.RegularExpressions;
using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.Naming;
using CleanCutPDF.Core.Pdf;
using CleanCutPDF.Core.Workspaces;

namespace CleanCutPDF.Core.Export;

public enum RenameMode
{
    /// <summary>Copy the PDF into the output folder under its new name (the original is untouched).</summary>
    CreateCopy,

    /// <summary>Rename the original file where it is.</summary>
    RenameInPlace
}

public sealed record RenameRequest(
    string SourcePath, ResolvedWorkspace Workspace, string ClientName, PartValues Values, int PageCount,
    RenameMode Mode, string OutputFolder);

public sealed record RenameResult(string SourcePath, string TargetPath);

/// <summary>Rename Only: one PDF is one document, named with the normal workspace fields (no SPLIT HERE markers).</summary>
public sealed class RenameService(ExportHistory history, AppLog log, TimeProvider? clock = null)
{
    private readonly TimeProvider _clock = clock ?? TimeProvider.System;

    /// <summary>The name the file will get (without folder), for showing before renaming.</summary>
    public static string ProposedName(ResolvedWorkspace workspace, string clientName, PartValues values)
    {
        var client = NameCasing.TitleCase(clientName.Trim());
        return FilenameBuilder.Render(workspace.FilenameTemplate, FilenameBuilder.BuildTokens(workspace, client, values)) + ".pdf";
    }

    public async Task<RenameResult> RenameAsync(RenameRequest request, CancellationToken cancellationToken = default)
    {
        var source = Path.GetFullPath(request.SourcePath);
        if (!File.Exists(source))
        {
            throw new FileNotFoundException($"{Path.GetFileName(source)} no longer exists.", source);
        }

        var client = NameCasing.TitleCase(request.ClientName.Trim());
        var tokens = FilenameBuilder.BuildTokens(request.Workspace, client, request.Values);
        var baseName = FilenameBuilder.Render(request.Workspace.FilenameTemplate, tokens);
        var folder = request.Mode == RenameMode.RenameInPlace ? Path.GetDirectoryName(source)! : request.OutputFolder;
        if (string.IsNullOrWhiteSpace(folder))
        {
            throw new InvalidOperationException("Choose an output folder first.");
        }

        Directory.CreateDirectory(folder);
        var target = UniqueTarget(folder, baseName, source);

        await Task.Run(() =>
        {
            if (request.Mode == RenameMode.RenameInPlace)
            {
                if (!string.Equals(target, source, StringComparison.OrdinalIgnoreCase))
                {
                    File.Move(source, target);
                }
            }
            else
            {
                File.Copy(source, target, overwrite: false);
            }
        }, cancellationToken);

        log.Info("Rename", $"{(request.Mode == RenameMode.RenameInPlace ? "Renamed" : "Copied")} " +
                           $"{Path.GetFileName(source)} → {Path.GetFileName(target)}");

        // Record it like an export so it appears in history and client suggestions.
        var part = new PartInput(new PageRange(0, Math.Max(0, request.PageCount - 1)), request.Values);
        var stamp = _clock.GetLocalNow().ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture);
        var line = $"[{stamp}] " + ExportService.HistoryLine(request.Workspace, client, Path.GetFileName(target), part, tokens, []);
        await history.AppendAsync([line], CancellationToken.None);
        return new RenameResult(source, target);
    }

    /// <summary>name.pdf, name_2.pdf, … — the file's own current name counts as free (renaming to the same name).</summary>
    internal static string UniqueTarget(string folder, string baseName, string source)
    {
        for (var counter = 1; ; counter++)
        {
            var candidate = Path.Combine(folder, counter == 1 ? $"{baseName}.pdf" : $"{baseName}_{counter}.pdf");
            if (!File.Exists(candidate) || string.Equals(Path.GetFullPath(candidate), source, StringComparison.OrdinalIgnoreCase))
            {
                return candidate;
            }
        }
    }
}

public static class QuickSplitOrders
{
    public const string OriginalThenPart = "Original Name - Part Number";
    public const string PartThenOriginal = "Part Number - Original Name";
    public const string OriginalOnly = "Original Name Only";
    public const string PartOnly = "Part Number Only";

    public static readonly IReadOnlyList<string> All = [OriginalThenPart, PartThenOriginal, OriginalOnly, PartOnly];
}

public sealed record QuickSplitResult(string OutputFolder, IReadOnlyList<ExportedFile> Files, bool NoMarkersFound);

/// <summary>
/// Quick Split: for batches where each client has one document. Splits at
/// SPLIT HERE pages, removes blank pages, and saves to
/// "Quick Split Files/YYYY-MM-DD" with generic names (1.x behavior).
/// </summary>
public sealed partial class QuickSplitService(IPdfEngine engine, AppLog log, TimeProvider? clock = null)
{
    private readonly SplitDetector _detector = new(engine, log);
    private readonly BlankPageDetector _blankPages = new(engine);
    private readonly TimeProvider _clock = clock ?? TimeProvider.System;

    public static string FileName(string originalName, int partNumber, string order)
    {
        var original = UnsafeCharacters().Replace(originalName, "_").Trim(' ', '.');
        if (original.Length == 0)
        {
            original = "Document";
        }

        var part = $"Part {partNumber:00}";
        return order switch
        {
            QuickSplitOrders.PartThenOriginal => $"{part} – {original}",
            QuickSplitOrders.OriginalOnly => original,
            QuickSplitOrders.PartOnly => part,
            _ => $"{original} – {part}"
        };
    }

    public async Task<QuickSplitResult> SplitAsync(string path, string exportRoot, string order, bool removeBlankPages,
        IProgress<string>? progress = null, CancellationToken cancellationToken = default)
    {
        var folder = Path.Combine(exportRoot, "Quick Split Files", _clock.GetLocalNow().ToString("yyyy-MM-dd", CultureInfo.InvariantCulture));
        Directory.CreateDirectory(folder);
        var name = Path.GetFileNameWithoutExtension(path);

        var detection = await _detector.DetectAsync(path,
            new Progress<DetectionProgress>(p => progress?.Report($"Finding SPLIT HERE pages… {p.PagesDone}/{p.PageCount}")),
            cancellationToken);

        var written = new List<ExportedFile>();
        try
        {
            for (var i = 0; i < detection.Ranges.Count; i++)
            {
                cancellationToken.ThrowIfCancellationRequested();
                progress?.Report($"Saving part {i + 1} of {detection.Ranges.Count}…");
                var range = detection.Ranges[i];
                var keep = new List<int>();
                var skipped = new List<int>();
                for (var page = range.Start; page <= range.End; page++)
                {
                    if (removeBlankPages && await _blankPages.IsBlankAsync(path, page, cancellationToken))
                    {
                        skipped.Add(page + 1);
                    }
                    else
                    {
                        keep.Add(page);
                    }
                }

                if (keep.Count == 0)
                {
                    keep = Enumerable.Range(range.Start, range.PageCount).ToList();
                    skipped.Clear();
                }

                var bytes = await engine.ExtractPagesAsync(path, keep, cancellationToken);
                var target = await ExportService.WriteUniqueAsync(folder, FileName(name, i + 1, order), bytes, cancellationToken);
                written.Add(new ExportedFile(target, range, skipped));
            }
        }
        catch
        {
            foreach (var file in written)
            {
                try
                {
                    File.Delete(file.Path);
                }
                catch
                {
                    // Best effort.
                }
            }

            throw;
        }

        log.Info("QuickSplit", $"{Path.GetFileName(path)}: {written.Count} file(s) saved to {folder}; " +
                               $"blank pages removed: {written.Sum(f => f.SkippedPages.Count)}");
        return new QuickSplitResult(folder, written, detection.NoMarkersInMultiPageDocument);
    }

    [GeneratedRegex("[\\\\/*?:\"<>|]")]
    private static partial Regex UnsafeCharacters();
}

/// <summary>
/// Remembered client names for suggestions: client folders in the export
/// folder plus every "Client:" in the export history. Built in the background
/// once and refreshed after exports (1.x re-read the whole log on every keystroke).
/// </summary>
public sealed partial class ClientNameIndex(ExportHistory history)
{
    private volatile IReadOnlyList<string> _names = [];

    public IReadOnlyList<string> Names => _names;

    public Task RefreshAsync(string? exportFolder, CancellationToken cancellationToken = default) => Task.Run(() =>
    {
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var names = new List<string>();
        void Add(string name)
        {
            name = name.Trim();
            if (name.Length > 0 && seen.Add(name))
            {
                names.Add(name);
            }
        }

        if (!string.IsNullOrWhiteSpace(exportFolder) && Directory.Exists(exportFolder))
        {
            try
            {
                foreach (var directory in new DirectoryInfo(exportFolder).EnumerateDirectories().OrderBy(d => d.Name, StringComparer.OrdinalIgnoreCase))
                {
                    if (!directory.Name.StartsWith('.') && !directory.Name.Equals("Quick Split Files", StringComparison.OrdinalIgnoreCase))
                    {
                        Add(directory.Name);
                    }
                }
            }
            catch (Exception error) when (error is IOException or UnauthorizedAccessException)
            {
                // A network folder may be offline; history still works.
            }
        }

        if (File.Exists(history.FilePath))
        {
            foreach (var line in File.ReadLines(history.FilePath))
            {
                var match = ClientPattern().Match(line);
                if (match.Success)
                {
                    Add(match.Groups[1].Value);
                }
            }
        }

        _names = names;
    }, cancellationToken);

    /// <summary>1.x ranking: name starts with the text, then a word starts with it, then contains it.</summary>
    public IReadOnlyList<string> Suggest(string? query, int limit = 3)
    {
        var text = (query ?? "").Trim();
        if (text.Length == 0)
        {
            return [];
        }

        return Names
            .Where(n => n.Contains(text, StringComparison.OrdinalIgnoreCase))
            .OrderBy(n => n.StartsWith(text, StringComparison.OrdinalIgnoreCase) ? 0
                : Words().Matches(n).Any(w => w.Value.StartsWith(text, StringComparison.OrdinalIgnoreCase)) ? 1 : 2)
            .ThenBy(n => n.IndexOf(text, StringComparison.OrdinalIgnoreCase))
            .ThenBy(n => n, StringComparer.OrdinalIgnoreCase)
            .Take(Math.Max(1, limit))
            .ToList();
    }

    [GeneratedRegex(@"\bClient:\s*([^|]+)", RegexOptions.IgnoreCase)]
    private static partial Regex ClientPattern();

    [GeneratedRegex("[A-Za-z0-9]+")]
    private static partial Regex Words();
}
