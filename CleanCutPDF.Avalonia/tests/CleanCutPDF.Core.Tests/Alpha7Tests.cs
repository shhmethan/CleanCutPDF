using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Naming;
using CleanCutPDF.Core.Services;
using CleanCutPDF.Core.Workspaces;

namespace CleanCutPDF.Core.Tests;

/// <summary>Fixes from the first week of real use: folder buttons and the Revoked toggle.</summary>
public sealed class Alpha7Tests : IDisposable
{
    private readonly TempDirectory _temp = new();
    private readonly AppPaths _paths;

    public Alpha7Tests()
    {
        _paths = new AppPaths(Path.Combine(_temp.Path, "data"), Path.Combine(_temp.Path, "legacy"));
        _paths.EnsureCreated();
    }

    // ───── Open Folder ─────

    [Fact]
    public void A_folder_saved_with_forward_slashes_is_opened_as_a_real_folder_path()
    {
        if (!OperatingSystem.IsWindows())
        {
            return;
        }

        // 1.x saved "C:/Users/…"; Explorer shows Documents when it is handed that.
        Assert.Equal(@"C:\Users\Ethan\Downloads\Processed Client Files\",
            ShellService.NormalizeFolder("C:/Users/Ethan/Downloads/Processed Client Files"));
        Assert.Equal(@"C:\Clients\Smith, John\", ShellService.NormalizeFolder(@"C:\Clients\Smith, John\"));
        Assert.Equal(@"C:\Clients\A\", ShellService.NormalizeFolder("  C:/Clients/B/../A//  "));
        Assert.Equal(@"C:\", ShellService.NormalizeFolder("C:/"));
    }

    [Fact]
    public void Open_folder_still_reports_a_missing_or_unset_folder()
    {
        var shell = new ShellService();
        Assert.Equal("Set the export folder first.", shell.OpenFolder("  ", "Export folder"));
        Assert.StartsWith("Export folder no longer exists", shell.OpenFolder(Path.Combine(_temp.Path, "gone"), "Export folder"));
    }

    // ───── Revoked in the Accounting file name ─────

    private static WorkspaceCatalog Saved(string template, params string[] fieldKeys)
    {
        var catalog = WorkspaceCatalog.CreateDefault();
        catalog.Revision = 0; // As read from a file written before the repair existed.
        var accounting = catalog.Find(WorkspaceCatalog.AccountingName);
        accounting.FilenameTemplate = template;
        accounting.FieldKeys = fieldKeys.ToList();
        return catalog;
    }

    [Theory]
    [InlineData("{client}_{agency_description}_{date}", "{client}_{revoked}_{agency_description}_{date}")]
    [InlineData("{date} {client}", "{date} {client}_{revoked}")]
    [InlineData("{agency_description}_{date}", "{revoked}_{agency_description}_{date}")]
    public void A_saved_Accounting_format_without_revoked_gets_it_once(string saved, string repaired)
    {
        var catalog = Saved(saved, "revoked", "agency", "description", "date");

        Assert.True(catalog.Upgrade());
        Assert.Equal(repaired, catalog.Find("Accounting").FilenameTemplate);

        // The toggle now reaches the file name…
        var workspace = catalog.Resolve("Accounting");
        var values = new PartValues { ["revoked"] = "true", ["agency"] = "f", ["description"] = "POA", ["date"] = "10-7-2026" };
        Assert.Contains("Revoked", FilenameBuilder.Render(workspace.FilenameTemplate, FilenameBuilder.BuildTokens(workspace, "John Smith", values)));

        // …and taking it out again afterwards is respected.
        catalog.Find("Accounting").FilenameTemplate = saved;
        Assert.False(catalog.Upgrade());
        Assert.Equal(saved, catalog.Find("Accounting").FilenameTemplate);
    }

    [Fact]
    public void The_default_file_name_is_unchanged_and_shows_Revoked_after_the_client()
    {
        var workspace = WorkspaceCatalog.CreateDefault().Resolve("Accounting");
        var values = new PartValues { ["revoked"] = "true", ["agency"] = "f", ["description"] = "POA", ["date"] = "10-7-2026" };
        Assert.Equal("John Smith_Revoked_FTB POA_10-07-2026",
            FilenameBuilder.Render(workspace.FilenameTemplate, FilenameBuilder.BuildTokens(workspace, "John Smith", values)));
    }

    [Theory]
    [InlineData("{client}{revoked}_{agency_description}", "revoked", "agency", "description", "date")] // Already there.
    [InlineData("{client}_{agency_description}_{date}", "agency", "description", "date")] // Toggle not in the workspace.
    public void Formats_that_need_no_repair_are_left_alone(string template, params string[] fieldKeys)
    {
        var catalog = Saved(template, fieldKeys);
        Assert.False(catalog.Upgrade());
        Assert.Equal(template, catalog.Find("Accounting").FilenameTemplate);
        Assert.Equal(WorkspaceCatalog.CurrentRevision, catalog.Revision);
    }

    [Fact]
    public void Other_workspaces_are_never_changed()
    {
        var catalog = Saved("{client}{revoked}", "revoked");
        var legal = catalog.Find("Legal");
        legal.FieldKeys.Add("revoked");
        var before = legal.FilenameTemplate;

        Assert.False(catalog.Upgrade());
        Assert.Equal(before, legal.FilenameTemplate);
    }

    [Fact]
    public async Task Loading_an_older_workspaces_file_repairs_it_and_saves_once()
    {
        var old = Saved("{client}_{agency_description}_{date}", "revoked", "agency", "description", "date");
        await File.WriteAllTextAsync(_paths.WorkspacesFile,
            System.Text.Json.JsonSerializer.Serialize(old, WorkspaceStore.JsonOptions).Replace("\"revision\": 0,", ""));
        Assert.DoesNotContain("\"revision\"", await File.ReadAllTextAsync(_paths.WorkspacesFile));

        var store = new WorkspaceStore(_paths);
        await store.LoadAsync();
        Assert.Equal("{client}_{revoked}_{agency_description}_{date}", store.Catalog.Find("Accounting").FilenameTemplate);
        Assert.Contains("{client}_{revoked}_{agency_description}_{date}", await File.ReadAllTextAsync(_paths.WorkspacesFile));

        // Removing it by hand afterwards sticks across restarts.
        store.Catalog.Find("Accounting").FilenameTemplate = "{client}_{date}";
        await store.SaveAsync();
        var again = new WorkspaceStore(_paths);
        await again.LoadAsync();
        Assert.Equal("{client}_{date}", again.Catalog.Find("Accounting").FilenameTemplate);
    }

    [Fact]
    public async Task A_first_start_without_a_file_writes_nothing()
    {
        var store = new WorkspaceStore(_paths);
        await store.LoadAsync();
        Assert.False(File.Exists(_paths.WorkspacesFile));
        Assert.Equal("{client}_{revoked}_{agency_description}_{date}", store.Catalog.Find("Accounting").FilenameTemplate);
    }

    [Fact]
    public async Task Importing_1x_settings_whose_Accounting_format_lacks_revoked_adds_it()
    {
        Directory.CreateDirectory(_paths.LegacyDataDirectory);
        await File.WriteAllTextAsync(Path.Combine(_paths.LegacyDataDirectory, "settings.json"), """
        {
          "workspaces": {
            "Accounting": {"filename_template": "{client}_{agency_description}_{date}",
                           "field_keys": ["revoked", "agency", "description", "date"], "permanent": true}
          }
        }
        """);

        var import = await new LegacyImporter(_paths).ReadAsync();

        Assert.Equal("{client}_{revoked}_{agency_description}_{date}", import.Catalog!.Find("Accounting").FilenameTemplate);
    }

    // ───── Workspaces editor note ─────

    [Fact]
    public void Fields_left_out_of_the_file_name_are_named()
    {
        var catalog = WorkspaceCatalog.CreateDefault();

        Assert.Empty(catalog.FieldsMissingFromFilename("Accounting", "{client}_{revoked}_{agency_description}_{date}"));
        Assert.Equal(["Revoked"], catalog.FieldsMissingFromFilename("Accounting", "{client}_{agency_description}_{date}"));
        Assert.Equal(["Revoked", "Description", "Date"], catalog.FieldsMissingFromFilename("Accounting", "{client}_{agency}"));
        Assert.Equal(["Document Type"], catalog.FieldsMissingFromFilename("Legal", "{client}_{matter_number}_{description}_{date}"));
    }

    public void Dispose() => _temp.Dispose();
}
