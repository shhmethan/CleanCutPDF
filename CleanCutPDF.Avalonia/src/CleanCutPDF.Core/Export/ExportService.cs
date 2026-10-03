using System.Globalization;
using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Naming;
using CleanCutPDF.Core.Pdf;
using CleanCutPDF.Core.Workspaces;

namespace CleanCutPDF.Core.Export;

public sealed record PartInput(PageRange Range, PartValues Values);

public sealed record ExportRequest(
    string SourcePath,
    ResolvedWorkspace Workspace,
    string ClientName,
    IReadOnlyList<PartInput> Parts,
    string OutputFolder,
    bool MakeClientFolder,
    bool RemoveBlankPages,
    string PartNoun = "Part");

/// <summary>Problems found before exporting, in the order 1.x reported them.</summary>
public sealed record ExportCheck(
    string? InvalidValue,
    IReadOnlyList<string> MissingRequired,
    IReadOnlyList<string> BlankOptionalDates,
    IReadOnlyList<string> FutureDates)
{
    public bool CanExport => InvalidValue is null && MissingRequired.Count == 0;
}

public readonly record struct ExportProgress(int PartsDone, int PartCount, string Stage);

public sealed record ExportedFile(string Path, PageRange Range, IReadOnlyList<int> SkippedPages);

public sealed record ExportResult(string OutputFolder, IReadOnlyList<ExportedFile> Files, IReadOnlyList<string> HistoryLines);

public static class ExportValidator
{
    public static ExportCheck Check(ResolvedWorkspace workspace, IReadOnlyList<PartInput> parts, DateOnly today,
        string partNoun = "Part")
    {
        var missing = new List<string>();
        var blankDates = new List<string>();
        var futureDates = new List<string>();

        for (var i = 0; i < parts.Count; i++)
        {
            var label = parts.Count == 1 && partNoun != "Part" ? partNoun : $"{partNoun} {i + 1}";
            var values = parts[i].Values;
            foreach (var field in workspace.Fields)
            {
                if (!FieldRules.IsVisible(field, values, workspace))
                {
                    continue;
                }

                var raw = values.Get(field.Key);
                var blank = field.IsBoolean ? !FieldDefinition.IsTrue(raw) : string.IsNullOrWhiteSpace(raw);
                if (field.Required && blank)
                {
                    missing.Add($"{label}: {field.Label}");
                    continue;
                }

                if (field.Type == FieldType.Date && blank && !field.Required)
                {
                    blankDates.Add($"{label}: {field.Label}");
                }

                if (blank)
                {
                    continue;
                }

                try
                {
                    if (field.Type == FieldType.Date)
                    {
                        if (DateFieldFormat.Parse(raw) > today)
                        {
                            futureDates.Add($"{label}: {field.Label} ({raw.Trim()})");
                        }
                    }
                    else if (field.Type == FieldType.Currency)
                    {
                        CurrencyFormat.Format(raw);
                    }
                }
                catch (FormatException error)
                {
                    return new ExportCheck($"{label} — {field.Label}:\n{error.Message}\n\nYou entered: {raw}",
                        missing, blankDates, futureDates);
                }
            }
        }

        return new ExportCheck(null, missing, blankDates, futureDates);
    }
}

/// <summary>Splits a PDF into one file per Part and records each file in the export history.</summary>
public sealed class ExportService(IPdfEngine engine, ExportHistory history, AppLog log, TimeProvider? clock = null)
{
    private readonly BlankPageDetector _blankPages = new(engine);
    private readonly TimeProvider _clock = clock ?? TimeProvider.System;

    public async Task<ExportResult> ExportAsync(ExportRequest request, IProgress<ExportProgress>? progress = null,
        CancellationToken cancellationToken = default)
    {
        var client = NameCasing.TitleCase(request.ClientName.Trim());
        var folder = request.MakeClientFolder && client.Length > 0
            ? Path.Combine(request.OutputFolder, FilenameBuilder.Sanitize(client))
            : request.OutputFolder;
        Directory.CreateDirectory(folder);

        var written = new List<ExportedFile>();
        var lines = new List<string>();
        var sourceName = Path.GetFileName(request.SourcePath);
        log.Info("Export", $"Exporting {sourceName}: {request.Parts.Count} part(s), workspace {request.Workspace.Name}");

        try
        {
            for (var i = 0; i < request.Parts.Count; i++)
            {
                cancellationToken.ThrowIfCancellationRequested();
                var part = request.Parts[i];
                progress?.Report(new ExportProgress(i, request.Parts.Count, $"{request.PartNoun} {i + 1} of {request.Parts.Count}"));

                var tokens = FilenameBuilder.BuildTokens(request.Workspace, client, part.Values);
                var baseName = FilenameBuilder.Render(request.Workspace.FilenameTemplate, tokens);

                var keep = new List<int>();
                var skipped = new List<int>();
                for (var page = part.Range.Start; page <= part.Range.End; page++)
                {
                    if (request.RemoveBlankPages && await _blankPages.IsBlankAsync(request.SourcePath, page, cancellationToken))
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
                    // Never produce an empty PDF: if every page looks blank, keep them all.
                    log.Warning("Export", $"{sourceName} part {i + 1}: every page looked blank; keeping all pages");
                    keep = Enumerable.Range(part.Range.Start, part.Range.PageCount).ToList();
                    skipped.Clear();
                }

                var bytes = await engine.ExtractPagesAsync(request.SourcePath, keep, cancellationToken);
                var path = await WriteUniqueAsync(folder, baseName, bytes, cancellationToken);
                written.Add(new ExportedFile(path, part.Range, skipped));
                lines.Add(HistoryLine(request.Workspace, client, Path.GetFileName(path), part, tokens, skipped));
                log.Info("Export", $"Wrote {Path.GetFileName(path)} (pages {part.Range}, {keep.Count} kept, {skipped.Count} blank removed)");
            }
        }
        catch (Exception error)
        {
            // An export is all-or-nothing so a failure never leaves a half-finished set of files.
            foreach (var file in written)
            {
                TryDelete(file.Path);
            }

            if (error is OperationCanceledException)
            {
                log.Info("Export", $"Cancelled {sourceName}; removed {written.Count} partial file(s)");
            }
            else
            {
                log.Error("Export", $"Export of {sourceName} failed; removed {written.Count} partial file(s)", error);
            }

            throw;
        }

        progress?.Report(new ExportProgress(request.Parts.Count, request.Parts.Count, "Done"));
        var stamp = _clock.GetLocalNow().ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture);
        var stamped = lines.Select(line => $"[{stamp}] {line}").ToList();
        await history.AppendAsync(stamped, CancellationToken.None);
        return new ExportResult(folder, written, stamped);
    }

    /// <summary>The 1.x export-log line, so old and new history can be read the same way.</summary>
    internal static string HistoryLine(ResolvedWorkspace workspace, string client, string fileName, PartInput part,
        IReadOnlyDictionary<string, string> tokens, IReadOnlyList<int> skipped)
    {
        var pairs = workspace.Fields
            .Where(f => FieldRules.IsVisible(f, part.Values, workspace))
            .Select(f => (f.Label, Value: tokens.TryGetValue(f.Key, out var v) ? v : ""))
            .Where(p => p.Value.Length > 0)
            .Select(p => $"{p.Label}={p.Value}")
            .ToList();
        string Token(string key) => tokens.TryGetValue(key, out var v) ? v : "";

        return $"Workspace: {workspace.Name} | Client: {client} | File: {fileName} | " +
               $"Pages: {part.Range.Start + 1}-{part.Range.End + 1} | " +
               $"Skipped: {(skipped.Count > 0 ? "[" + string.Join(", ", skipped) + "]" : "None")} | " +
               $"Agency: {Token("agency")} | Desc: {Token("description")} | " +
               $"Date: {(Token("date").Length > 0 ? Token("date") : "None")} | " +
               $"Revoked: {(Token("revoked") == "Revoked" ? "True" : "False")} | " +
               $"Matter: {Token("matter_number")} | Document Type: {Token("document_type")} | " +
               $"Fields: {(pairs.Count > 0 ? string.Join("; ", pairs) : "None")}";
    }

    /// <summary>Writes name.pdf, or name_2.pdf, name_3.pdf… so nothing is ever overwritten.</summary>
    internal static async Task<string> WriteUniqueAsync(string folder, string baseName, byte[] bytes,
        CancellationToken cancellationToken)
    {
        for (var counter = 1; ; counter++)
        {
            var path = Path.Combine(folder, counter == 1 ? $"{baseName}.pdf" : $"{baseName}_{counter}.pdf");
            if (File.Exists(path))
            {
                continue;
            }

            try
            {
                await using var stream = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.None);
                await stream.WriteAsync(bytes, cancellationToken);
                return path;
            }
            catch (IOException) when (File.Exists(path))
            {
                // Another process created the same name in the meantime; try the next one.
            }
        }
    }

    private static void TryDelete(string path)
    {
        try
        {
            File.Delete(path);
        }
        catch
        {
            // Best effort.
        }
    }
}

/// <summary>export-history.log: one line per exported file, bounded like 1.x (2,500 lines once over 4 MB).</summary>
public sealed class ExportHistory(AppPaths paths, IRecycleBin? recycleBin = null)
{
    private const long MaxBytes = 4L * 1024 * 1024;
    private const int KeepLines = 2500;
    private readonly SemaphoreSlim _gate = new(1, 1);

    public string FilePath => paths.ExportHistoryFile;

    /// <summary>Raised after the history changes (export, rename, import, undo, clear).</summary>
    public event EventHandler? Changed;

    /// <summary>All history lines, read off the UI thread.</summary>
    public async Task<IReadOnlyList<string>> ReadLinesAsync(CancellationToken cancellationToken = default)
    {
        await _gate.WaitAsync(cancellationToken);
        try
        {
            return File.Exists(FilePath) ? await File.ReadAllLinesAsync(FilePath, cancellationToken) : [];
        }
        finally
        {
            _gate.Release();
        }
    }

    /// <summary>Puts older lines (e.g. imported 1.x history) before the existing ones, skipping duplicates.</summary>
    public async Task PrependAsync(IReadOnlyList<string> olderLines, CancellationToken cancellationToken = default)
    {
        await _gate.WaitAsync(cancellationToken);
        try
        {
            var existing = File.Exists(FilePath) ? await File.ReadAllLinesAsync(FilePath, cancellationToken) : [];
            var known = existing.ToHashSet();
            var combined = olderLines.Where(l => !known.Contains(l)).Concat(existing).TakeLast(KeepLines * 4);
            await AtomicFile.WriteAllTextAsync(FilePath, string.Join(Environment.NewLine, combined) + Environment.NewLine,
                cancellationToken);
        }
        finally
        {
            _gate.Release();
        }

        Changed?.Invoke(this, EventArgs.Empty);
    }

    public async Task AppendAsync(IReadOnlyList<string> lines, CancellationToken cancellationToken = default)
    {
        await _gate.WaitAsync(cancellationToken);
        try
        {
            paths.EnsureCreated();
            await File.AppendAllLinesAsync(FilePath, lines, cancellationToken);
            if (new FileInfo(FilePath).Length > MaxBytes)
            {
                var retained = (await File.ReadAllLinesAsync(FilePath, cancellationToken)).TakeLast(KeepLines);
                await AtomicFile.WriteAllTextAsync(FilePath, string.Join(Environment.NewLine, retained) + Environment.NewLine,
                    cancellationToken);
            }
        }
        finally
        {
            _gate.Release();
        }

        Changed?.Invoke(this, EventArgs.Empty);
    }

    /// <summary>Clear Log: the old history goes to the Recycle Bin (so it can be restored), and a new one starts.</summary>
    public async Task<string?> ClearAsync()
    {
        string? problem = null;
        await _gate.WaitAsync();
        try
        {
            if (File.Exists(FilePath))
            {
                var stamped = Path.Combine(Path.GetDirectoryName(FilePath)!, $"export-history {DateTime.Now:yyyy-MM-dd HHmmss}.log");
                File.Move(FilePath, stamped);
                problem = (recycleBin ?? new SystemRecycleBin()).Recycle(stamped);
            }
        }
        finally
        {
            _gate.Release();
        }

        Changed?.Invoke(this, EventArgs.Empty);
        return problem;
    }
}
