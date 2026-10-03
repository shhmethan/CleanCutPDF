using System.Text.Json;
using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Models;
using CleanCutPDF.Core.Pdf;

namespace CleanCutPDF.Core.Sessions;

public sealed class SessionFolder
{
    public const string InboxId = "inbox";

    public string Id { get; set; } = "";
    public string Name { get; set; } = "";
}

/// <summary>One open PDF and everything typed into it.</summary>
public sealed class SessionDocument
{
    public string FilePath { get; set; } = "";
    public string ClientName { get; set; } = "";
    public string Workspace { get; set; } = "";
    public string FolderId { get; set; } = SessionFolder.InboxId;
    public int PageCount { get; set; }
    public FileSignature? FileSignature { get; set; }

    /// <summary>Cached split detection; trusted only while the file signature matches.</summary>
    public List<PageRange>? DetectedRanges { get; set; }

    public List<int> MarkerPages { get; set; } = [];

    /// <summary>Workspace name → one value dictionary per Part (kept per workspace so switching back restores them).</summary>
    public Dictionary<string, List<Dictionary<string, string>>> WorkspaceData { get; set; } = new();
}

public sealed class SessionState
{
    public int SchemaVersion { get; set; } = 1;
    public List<SessionFolder> Folders { get; set; } = [];
    public List<SessionDocument> Documents { get; set; } = [];

    /// <summary>Inbox always exists and stays first.</summary>
    public void Normalize()
    {
        Folders = Folders
            .Where(f => !string.IsNullOrWhiteSpace(f.Id) && !string.IsNullOrWhiteSpace(f.Name))
            .GroupBy(f => f.Id).Select(g => g.First())
            .Where(f => f.Id != SessionFolder.InboxId)
            .ToList();
        Folders.Insert(0, new SessionFolder { Id = SessionFolder.InboxId, Name = "Inbox" });

        var folderIds = Folders.Select(f => f.Id).ToHashSet();
        foreach (var document in Documents.Where(d => !folderIds.Contains(d.FolderId)))
        {
            document.FolderId = SessionFolder.InboxId;
        }
    }
}

/// <summary>sessions.json: open documents, Inbox folders, and entered values.</summary>
public sealed class SessionStore(AppPaths paths, AppLog log)
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower
    };

    private readonly SemaphoreSlim _gate = new(1, 1);

    public async Task<SessionState> LoadAsync(CancellationToken cancellationToken = default)
    {
        var state = new SessionState();
        try
        {
            if (File.Exists(paths.SessionsFile))
            {
                await using var stream = File.OpenRead(paths.SessionsFile);
                state = await JsonSerializer.DeserializeAsync<SessionState>(stream, JsonOptions, cancellationToken) ?? state;
            }
        }
        catch (JsonException error)
        {
            log.Error("Session", "sessions.json was unreadable; starting with an empty Inbox", error);
        }

        state.Normalize();
        return state;
    }

    public async Task SaveAsync(SessionState state, CancellationToken cancellationToken = default)
    {
        state.Normalize();
        var json = JsonSerializer.Serialize(state, JsonOptions);
        await _gate.WaitAsync(cancellationToken);
        try
        {
            await AtomicFile.WriteAllTextAsync(paths.SessionsFile, json, cancellationToken);
        }
        finally
        {
            _gate.Release();
        }
    }

    /// <summary>
    /// Keeps saved values but always trusts the current ranges (1.x
    /// reconcile_workspace_data_ranges): rows are matched by Part index.
    /// </summary>
    public static Dictionary<string, List<Dictionary<string, string>>> Reconcile(
        Dictionary<string, List<Dictionary<string, string>>> data, int partCount) =>
        data.ToDictionary(
            pair => pair.Key,
            pair => Enumerable.Range(0, partCount)
                .Select(i => i < pair.Value.Count ? new Dictionary<string, string>(pair.Value[i]) : new Dictionary<string, string>())
                .ToList());
}
