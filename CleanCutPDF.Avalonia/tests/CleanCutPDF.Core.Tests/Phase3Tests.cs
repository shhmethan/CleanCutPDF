using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.Export;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Models;
using CleanCutPDF.Core.Naming;
using CleanCutPDF.Core.Pdf;
using CleanCutPDF.Core.Services;
using CleanCutPDF.Core.Workspaces;

namespace CleanCutPDF.Core.Tests;

public sealed class Phase3Tests : IAsyncDisposable
{
    private readonly TempDirectory _temp = new();
    private readonly PdfiumEngine _engine = new();
    private readonly AppPaths _paths;
    private readonly AppLog _log;

    public Phase3Tests()
    {
        _paths = new AppPaths(Path.Combine(_temp.Path, "data"), Path.Combine(_temp.Path, "legacy"));
        _log = new AppLog(_paths);
    }

    // ───── Workspace editing ─────

    [Fact]
    public void Workspaces_can_be_added_renamed_and_deleted_but_accounting_is_permanent()
    {
        var catalog = WorkspaceCatalog.CreateDefault();

        var deposits = catalog.AddWorkspace("  Deposits ");
        Assert.Equal("Deposits", deposits.Name);
        Assert.Equal("{client}_{date}", deposits.FilenameTemplate);
        Assert.Throws<WorkspaceEditException>(() => catalog.AddWorkspace("deposits"));

        catalog.RenameWorkspace("Deposits", "Bank Deposits");
        Assert.Contains("Bank Deposits", catalog.WorkspaceNames);
        Assert.Throws<WorkspaceEditException>(() => catalog.RenameWorkspace("Accounting", "Tax"));
        Assert.Throws<WorkspaceEditException>(() => catalog.DeleteWorkspace("Accounting"));

        catalog.DeleteWorkspace("Bank Deposits");
        Assert.DoesNotContain("Bank Deposits", catalog.WorkspaceNames);
    }

    [Fact]
    public void Custom_fields_get_keys_and_deleting_cleans_up_references()
    {
        var catalog = WorkspaceCatalog.CreateDefault();
        var first = catalog.AddField("Invoice #");
        var second = catalog.AddField("Invoice #");
        Assert.Equal("invoice", first.Key);
        Assert.Equal("invoice_2", second.Key);

        var legal = catalog.Find("Legal");
        legal.AssignField("invoice");
        legal.Notes.Add(new WorkspaceNote { Text = "Check the invoice", BeforeField = "invoice" });
        catalog.Fields["amount"].Condition = new FieldCondition { Field = "invoice", EqualsValue = "x" };

        catalog.DeleteField("invoice");

        Assert.DoesNotContain("invoice", legal.FieldKeys);
        Assert.Equal(WorkspaceNote.EndOfForm, legal.Notes[0].BeforeField);
        Assert.Null(catalog.Fields["amount"].Condition);
        Assert.Throws<WorkspaceEditException>(() => catalog.DeleteField("date")); // built-in
    }

    [Fact]
    public void Fields_reorder_within_a_workspace()
    {
        var accounting = WorkspaceCatalog.CreateDefault().Find("Accounting");
        accounting.MoveField("date", -1);
        Assert.Equal(["revoked", "agency", "date", "description"], accounting.FieldKeys);
        accounting.MoveField("revoked", -1); // already first: no change
        Assert.Equal("revoked", accounting.FieldKeys[0]);
    }

    // ───── Rename Only ─────

    [Fact]
    public async Task Rename_creates_copy_or_renames_in_place_without_overwriting()
    {
        var source = RawPdf.Write(_temp.Path, "scan001.pdf", RawPdf.Text("Hello"));
        var workspace = WorkspaceCatalog.CreateDefault().Resolve("Accounting");
        var values = new PartValues { ["revoked"] = "false", ["agency"] = "i", ["description"] = "poa", ["date"] = "082026" };
        var output = Path.Combine(_temp.Path, "renamed");
        var service = new RenameService(new ExportHistory(_paths), _log);

        Assert.Equal("Jane Doe_IRS POA_8-20-2026.pdf", RenameService.ProposedName(workspace, "jane doe", values));

        var copy = await service.RenameAsync(new RenameRequest(source, workspace, "jane doe", values, 1, RenameMode.CreateCopy, output));
        var copy2 = await service.RenameAsync(new RenameRequest(source, workspace, "jane doe", values, 1, RenameMode.CreateCopy, output));
        Assert.Equal("Jane Doe_IRS POA_8-20-2026.pdf", Path.GetFileName(copy.TargetPath));
        Assert.Equal("Jane Doe_IRS POA_8-20-2026_2.pdf", Path.GetFileName(copy2.TargetPath));
        Assert.True(File.Exists(source));

        var moved = await service.RenameAsync(new RenameRequest(source, workspace, "jane doe", values, 1, RenameMode.RenameInPlace, ""));
        Assert.False(File.Exists(source));
        Assert.Equal(_temp.Path, Path.GetDirectoryName(moved.TargetPath));
        Assert.Contains("Client: Jane Doe", (await File.ReadAllLinesAsync(_paths.ExportHistoryFile))[0]);
    }

    // ───── Quick Split ─────

    [Theory]
    [InlineData(QuickSplitOrders.OriginalThenPart, "Scan – Part 03")]
    [InlineData(QuickSplitOrders.PartThenOriginal, "Part 03 – Scan")]
    [InlineData(QuickSplitOrders.OriginalOnly, "Scan")]
    [InlineData(QuickSplitOrders.PartOnly, "Part 03")]
    public void Quick_split_names_match_1x(string order, string expected) =>
        Assert.Equal(expected, QuickSplitService.FileName("Scan", 3, order));

    [Fact]
    public async Task Quick_split_saves_dated_folder_with_blank_pages_removed()
    {
        var source = RawPdf.Write(_temp.Path, "batch.pdf",
            RawPdf.Text("Client A"), RawPdf.Blank, RawPdf.Text("SPLIT HERE", 48, 150, 400), RawPdf.Text("Client B"));
        var root = Path.Combine(_temp.Path, "exports");
        var service = new QuickSplitService(_engine, _log, new FakeClock(new DateTimeOffset(2026, 10, 2, 8, 0, 0, TimeSpan.Zero)));

        var result = await service.SplitAsync(source, root, QuickSplitOrders.OriginalThenPart, removeBlankPages: true);

        Assert.Equal(Path.Combine(root, "Quick Split Files", "2026-10-02"), result.OutputFolder);
        Assert.Equal(["batch – Part 01.pdf", "batch – Part 02.pdf"], result.Files.Select(f => Path.GetFileName(f.Path)));
        Assert.Equal(1, (await _engine.OpenAsync(result.Files[0].Path)).PageCount);
        Assert.False(result.NoMarkersFound);
    }

    // ───── Client suggestions ─────

    [Fact]
    public async Task Client_suggestions_come_from_folders_and_history_ranked_like_1x()
    {
        var exports = Path.Combine(_temp.Path, "out");
        foreach (var folder in new[] { "Smithson LLC", "Quick Split Files", ".hidden", "Adam Smith" })
        {
            Directory.CreateDirectory(Path.Combine(exports, folder));
        }

        var history = new ExportHistory(_paths);
        await history.AppendAsync(["[2026-01-01 10:00:00] Workspace: Accounting | Client: Smith Family Trust | File: x.pdf",
                                   "[2026-01-02 10:00:00] Workspace: Accounting | Client: adam smith | File: y.pdf"]);
        var index = new ClientNameIndex(history);

        await index.RefreshAsync(exports);

        Assert.Equal(["Adam Smith", "Smithson LLC", "Smith Family Trust"], index.Names); // de-duplicated, case-insensitive
        Assert.Equal(["Smith Family Trust", "Smithson LLC", "Adam Smith"], index.Suggest("smith"));
        Assert.Empty(index.Suggest(""));
    }

    // ───── 1.x import ─────

    [Fact]
    public async Task Legacy_data_imports_read_only_with_1x_migrations()
    {
        var legacy = _paths.LegacyDataDirectory;
        Directory.CreateDirectory(legacy);
        var pdf = RawPdf.Write(_temp.Path, "saved.pdf", RawPdf.Text("A"), RawPdf.Text("SPLIT HERE", 48), RawPdf.Text("B"));
        var info = new FileInfo(pdf);
        var mtimeNs = (info.LastWriteTimeUtc.Ticks - DateTime.UnixEpoch.Ticks) * 100;
        var legacyPdf = pdf.Replace("\\", "\\\\");

        var settingsJson = """
        {
          "theme": "Dark Pink", "export_folder": "C:/Out", "default_workspace": "Deposits",
          "suppressFutureDateWarning": true, "remove_blank_pages": false,
          "quick_split_filename_order": "Part Number Only",
          "folder_shortcuts": [{"label": "Mail", "path": "C:/Mail", "icon": "📥", "color": "#FF0000"}],
          "custom_fields": {
            "agency": {"label": "Agency", "type": "text", "default": "", "autofill": true, "system": true},
            "ref_no": {"label": "Ref No", "type": "number", "default": "", "required": true,
                       "condition": {"field": "payment_method", "equals": "CK"}},
            "urgent": {"label": "Urgent", "type": "toggle", "default": true}
          },
          "workspaces": {
            "Accounting": {"client_label": "Client", "filename_template": "{client}_{date}", "field_keys": ["agency", "date", "ghost"], "permanent": true},
            "Deposits": {"client_label": "Payer", "summary": "Deposits", "filename_template": "{client}_{ref_no}",
                         "field_keys": ["ref_no", "urgent"], "notes": [{"id": "n1", "text": "Stamp it", "before_field": "ref_no"}],
                         "field_overrides": {"urgent": {"default": false}}}
          },
          "workspace_settings": {"Accounting": {"filename_template": "{client}_{agency}", "default_description": "POA", "autofill_description": true}}
        }
        """;
        await File.WriteAllTextAsync(Path.Combine(legacy, "settings.json"), settingsJson);
        await File.WriteAllTextAsync(Path.Combine(legacy, "document_project.json"),
            """{"folders": [{"id": "inbox", "name": "Inbox", "parent_id": null}, {"id": "f-1", "name": "Banks", "parent_id": null}]}""");
        await File.WriteAllTextAsync(Path.Combine(legacy, "sessions.json"), $$$"""
        [{"file_path": "{{{legacyPdf}}}", "client_name": "Acme", "workspace": "Deposits", "folder_id": "f-1",
          "detected_ranges": [{"start": 0, "end": 0}, {"start": 2, "end": 2}],
          "file_signature": {"size": {{{info.Length}}}, "mtime_ns": {{{mtimeNs}}}},
          "workspace_data": {"Deposits": [{"range": {"start": 0, "end": 0}, "ref_no": "12", "urgent": true}]}},
         {"file_path": "C:/gone/missing.pdf", "workspace": "Accounting"}]
        """);
        await File.WriteAllLinesAsync(Path.Combine(legacy, "full.log"),
            ["[2026-01-01 10:00:00] Workspace: Accounting | Client: Acme | File: a.pdf", "[2026-01-01 10:00:01] Export folder changed"]);
        var before = Directory.GetFiles(legacy).ToDictionary(f => f, File.ReadAllText);

        var import = await new LegacyImporter(_paths).ReadAsync();

        // Workspaces and fields
        var catalog = import.Catalog!;
        Assert.Equal(["Accounting", "Deposits"], catalog.WorkspaceNames);
        Assert.Equal("{client}_{agency}", catalog.Find("Accounting").FilenameTemplate); // v1.8 migration
        Assert.Equal(["agency", "date"], catalog.Find("Accounting").FieldKeys); // unknown field dropped
        var deposits = catalog.Resolve("Deposits");
        Assert.Equal("Payer", deposits.ClientLabel);
        Assert.Equal(FieldType.Number, deposits.Field("ref_no")!.Type);
        Assert.True(deposits.Field("ref_no")!.Required);
        Assert.Equal("CK", deposits.Field("ref_no")!.Condition!.EqualsValue);
        Assert.Equal("false", deposits.Field("urgent")!.Default); // override applied, bool → text
        Assert.Equal("ref_no", deposits.Notes[0].BeforeField);
        Assert.Contains("date", catalog.Fields.Keys); // built-ins kept

        // Settings
        var settings = new AppSettings();
        import.ApplySettings!(settings);
        Assert.Equal(AppThemeMode.Dark, settings.Theme);
        Assert.Equal("C:/Out", settings.ExportFolder);
        Assert.Equal("Deposits", settings.DefaultWorkspace);
        Assert.False(settings.WarnOnFutureDates);
        Assert.False(settings.RemoveBlankPages);
        Assert.Equal(QuickSplitOrders.PartOnly, settings.QuickSplitFilenameOrder);
        Assert.Equal("Mail", Assert.Single(settings.FolderShortcuts).Label);

        // Session, folders, history
        var document = Assert.Single(import.Session.Documents);
        Assert.Equal("Acme", document.ClientName);
        Assert.Equal("f-1", document.FolderId);
        Assert.Equal(FileSignature.TryRead(pdf), document.FileSignature); // nanoseconds converted exactly
        Assert.Equal("true", document.WorkspaceData["Deposits"][0]["urgent"]);
        Assert.False(document.WorkspaceData["Deposits"][0].ContainsKey("range"));
        Assert.Contains(import.Session.Folders, f => f.Name == "Banks");
        Assert.Single(import.HistoryLines);
        Assert.Contains(import.Warnings, w => w.Contains("missing.pdf"));

        // Nothing in the 1.x folder changed.
        Assert.All(before, pair => Assert.Equal(pair.Value, File.ReadAllText(pair.Key)));
    }

    public async ValueTask DisposeAsync()
    {
        _engine.Dispose();
        await _log.DisposeAsync();
        _temp.Dispose();
    }
}
