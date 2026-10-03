using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Models;
using CleanCutPDF.Core.Pdf;
using CleanCutPDF.Core.Sessions;
using CleanCutPDF.Core.Workspaces;

namespace CleanCutPDF.Core.Tests;

public sealed class SessionStoreTests : IAsyncDisposable
{
    private readonly TempDirectory _temp = new();
    private readonly AppPaths _paths;
    private readonly AppLog _log;

    public SessionStoreTests()
    {
        _paths = new AppPaths(_temp.Path, Path.Combine(_temp.Path, "legacy"));
        _log = new AppLog(_paths);
    }

    [Fact]
    public async Task Session_round_trips_and_inbox_is_always_first()
    {
        var store = new SessionStore(_paths, _log);
        var state = new SessionState
        {
            Folders = [new SessionFolder { Id = "f1", Name = "Deposits" }],
            Documents =
            [
                new SessionDocument
                {
                    FilePath = "C:/scans/a.pdf", ClientName = "Acme", Workspace = "Legal", FolderId = "f1",
                    PageCount = 5, FileSignature = new FileSignature(10, 20),
                    DetectedRanges = [new PageRange(0, 1), new PageRange(3, 4)], MarkerPages = [2],
                    WorkspaceData = { ["Legal"] = [new() { ["description"] = "Letter" }, new()] }
                },
                new SessionDocument { FilePath = "C:/scans/b.pdf", FolderId = "deleted-folder" }
            ]
        };

        await store.SaveAsync(state);
        var loaded = await store.LoadAsync();

        Assert.Equal(["inbox", "f1"], loaded.Folders.Select(f => f.Id));
        var a = loaded.Documents[0];
        Assert.Equal("Acme", a.ClientName);
        Assert.Equal(new FileSignature(10, 20), a.FileSignature);
        Assert.Equal([new PageRange(0, 1), new PageRange(3, 4)], a.DetectedRanges);
        Assert.Equal("Letter", a.WorkspaceData["Legal"][0]["description"]);
        Assert.Equal(SessionFolder.InboxId, loaded.Documents[1].FolderId); // orphan moved to Inbox
    }

    [Fact]
    public void Reconcile_keeps_values_by_part_index()
    {
        var data = new Dictionary<string, List<Dictionary<string, string>>>
        {
            ["Accounting"] = [new() { ["agency"] = "i" }, new() { ["agency"] = "f" }, new() { ["agency"] = "e" }]
        };

        var two = SessionStore.Reconcile(data, 2);
        var four = SessionStore.Reconcile(data, 4);

        Assert.Equal(["i", "f"], two["Accounting"].Select(r => r["agency"]));
        Assert.Equal(4, four["Accounting"].Count);
        Assert.Empty(four["Accounting"][3]);
    }

    [Fact]
    public async Task Workspace_catalog_persists_and_repairs()
    {
        var store = new WorkspaceStore(_paths, _log);
        await store.LoadAsync();
        store.Catalog.Workspaces.RemoveAll(w => w.Name == "Accounting");
        store.Catalog.Workspaces.Add(new WorkspaceDefinition { Name = "Deposits", FieldKeys = ["amount", "missing_field"] });
        await store.SaveAsync();

        var reloaded = new WorkspaceStore(_paths, _log);
        await reloaded.LoadAsync();

        Assert.Contains("Accounting", reloaded.Catalog.WorkspaceNames);
        Assert.Equal(["amount"], reloaded.Catalog.Resolve("Deposits").Fields.Select(f => f.Key));
    }

    public async ValueTask DisposeAsync()
    {
        await _log.DisposeAsync();
        _temp.Dispose();
    }
}
