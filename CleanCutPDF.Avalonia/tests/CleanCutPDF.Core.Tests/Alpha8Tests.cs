using CleanCutPDF.Core.Export;
using CleanCutPDF.Core.History;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Models;
using CleanCutPDF.Core.Naming;
using CleanCutPDF.Core.Services;
using CleanCutPDF.Core.Workspaces;

namespace CleanCutPDF.Core.Tests;

/// <summary>Requests from the second round of real use: suggestions, and refilling a renamed file's fields.</summary>
public sealed class Alpha8Tests : IDisposable
{
    private const string MailFile = "2026.10.09 $10.98 IRS 2025 Form 1040 Extension Request- Espinosa, Diego Patricio & Sonia.pdf";

    private readonly TempDirectory _temp = new();
    private readonly AppPaths _paths;

    public Alpha8Tests()
    {
        _paths = new AppPaths(Path.Combine(_temp.Path, "data"), Path.Combine(_temp.Path, "legacy"));
        _paths.EnsureCreated();
    }

    public void Dispose() => _temp.Dispose();

    /// <summary>The default catalog plus the user's "Mail" workspace.</summary>
    private static WorkspaceCatalog MailCatalog()
    {
        var catalog = WorkspaceCatalog.CreateDefault();
        catalog.Fields["date_acc"] = new FieldDefinition
        {
            Key = "date_acc", Label = "Date (ACC)", Type = FieldType.Date, DateFormat = "YYYY.MM.DD"
        };
        catalog.Workspaces.Add(new WorkspaceDefinition
        {
            Name = "Mail",
            ClientLabel = "Client Name",
            FilenameTemplate = "{date_acc} {amount} {description}- {client} {company}",
            FieldKeys = ["date_acc", "description", "amount", "company"]
        });
        return catalog;
    }

    // ───── Client suggestions ─────

    [Fact]
    public async Task Suggestions_list_more_than_three_names_and_leave_out_hidden_ones_until_exported_again()
    {
        var history = new ExportHistory(_paths);
        await history.AppendAsync([
            "[2026-10-01 09:00:00] Workspace: Mail | Client: Lawrence, Denise K. Winslow | File: a.pdf",
            "[2026-10-02 09:00:00] Workspace: Mail | Client: Lawrence, Patri | File: b.pdf",
            "[2026-10-03 09:00:00] Workspace: Mail | Client: Lawrence, Patrick | File: c.pdf",
            "[2026-10-04 09:00:00] Workspace: Mail | Client: Lawrence, Patrick & Denise K. Winslow | File: d.pdf",
            "[2026-10-05 09:00:00] Workspace: Mail | Client: Lawrence Family Trust | File: e.pdf"
        ]);
        var index = new ClientNameIndex(history);
        await index.RefreshAsync();

        Assert.Equal(5, index.Suggest("lawrence").Count); // 1.x stopped at 3.
        Assert.Equal(new DateTime(2026, 10, 2, 9, 0, 0), index.LastUsed("lawrence, patri"));

        var hidden = new Dictionary<string, DateTime> { ["lawrence, PATRI"] = new(2026, 10, 10) };
        Assert.DoesNotContain("Lawrence, Patri", index.Suggest("lawrence", hidden: hidden));
        Assert.Contains("Lawrence, Patrick", index.Suggest("patri", hidden: hidden));

        // Exported again after it was hidden: it is a real name after all.
        await history.AppendAsync(["[2026-10-12 09:00:00] Workspace: Mail | Client: Lawrence, Patri | File: f.pdf"]);
        await index.RefreshAsync();
        Assert.Contains("Lawrence, Patri", index.Suggest("lawrence", hidden: hidden));
    }

    [Fact]
    public void Reset_settings_keeps_hidden_client_names()
    {
        var current = new AppSettings { HiddenClientNames = { ["Lawrence, Patri"] = new DateTime(2026, 10, 10) } };

        var reset = SettingsReset.Defaults(current);

        Assert.Equal(new DateTime(2026, 10, 10), reset.HiddenClientNames["Lawrence, Patri"]);
        current.HiddenClientNames.Clear();
        Assert.Single(reset.HiddenClientNames); // A copy, not the same dictionary.
        Assert.NotSame(current.Clone().HiddenClientNames, current.HiddenClientNames);
    }

    // ───── Refill from the export log ─────

    [Fact]
    public void A_file_in_the_export_log_gets_its_workspace_client_and_fields_back()
    {
        var line = "[2026-10-09 13:05:00] Workspace: Mail | Client: Espinosa, Diego Patricio & Sonia | File: " + MailFile +
                   " | Pages: 1-11 | Skipped: None | Agency:  | Desc: IRS 2025 Form 1040 Extension Request | Date: None | " +
                   "Revoked: False | Matter:  | Document Type:  | " +
                   "Fields: Date (ACC)=2026.10.09; Description=IRS 2025 Form 1040 Extension Request; Amount=$10.98";
        var history = HistoryLog.Parse([line]);

        var result = FilenameRecognizer.Recognize(MailFile.ToUpperInvariant(), MailCatalog(), history, [], "Accounting");

        Assert.NotNull(result);
        Assert.Equal(RecognitionSource.ExportLog, result.Source);
        Assert.Equal("Mail", result.Workspace);
        Assert.Equal("Espinosa, Diego Patricio & Sonia", result.Client);
        Assert.Equal("2026.10.09", result.Values["date_acc"]);
        Assert.Equal("IRS 2025 Form 1040 Extension Request", result.Values["description"]);
        Assert.Equal("$10.98", result.Values["amount"]);
        Assert.Equal("", result.Values["company"]);
        Assert.Equal(new DateTime(2026, 10, 9, 13, 5, 0), result.ExportedAt);
    }

    [Fact]
    public void Logged_values_may_contain_semicolons_and_booleans_come_back_as_true()
    {
        var workspace = WorkspaceCatalog.CreateDefault().Resolve("Accounting");

        var values = FilenameRecognizer.ParseFields("Revoked=Revoked; Agency Code=IRS; Description=Notice; Penalty; Date=8-20-2026", workspace);

        Assert.Equal("Notice; Penalty", values["description"]);
        Assert.Equal("Revoked", values["revoked"]);
        var line = "[2026-08-21 10:00:00] Workspace: Accounting | Client: Smith | File: Smith_Revoked_IRS Notice_8-20-2026.pdf | " +
                   "Fields: Revoked=Revoked; Agency Code=IRS; Description=Notice; Date=8-20-2026";
        var result = FilenameRecognizer.FromHistory("Smith_Revoked_IRS Notice_8-20-2026.pdf", WorkspaceCatalog.CreateDefault(),
            HistoryLog.Parse([line]));
        Assert.Equal("true", result!.Values["revoked"]);
        Assert.Equal("IRS", result.Values["agency"]);
    }

    // ───── Refill from the filename format ─────

    [Fact]
    public void A_file_not_in_the_log_is_read_with_the_workspace_filename_format()
    {
        var result = FilenameRecognizer.Recognize(MailFile, MailCatalog(), [], [], "Accounting");

        Assert.NotNull(result);
        Assert.Equal(RecognitionSource.FilenameFormat, result.Source);
        Assert.Equal("Mail", result.Workspace);
        // With nothing else to go on, the whole tail is the client (Company is empty).
        Assert.Equal("Espinosa, Diego Patricio & Sonia", result.Client);
        Assert.Equal("2026.10.09", result.Values["date_acc"]);
        Assert.Equal("$10.98", result.Values["amount"]);
        Assert.Equal("IRS 2025 Form 1040 Extension Request", result.Values["description"]);
        Assert.Equal("", result.Values["company"]);
    }

    [Fact]
    public void A_known_client_and_a_company_are_split_correctly_and_name_2_is_understood()
    {
        var file = "2026.10.09 $10.98 IRS Notice- Espinosa, Diego JARB LLC_2.pdf";

        var result = FilenameRecognizer.Recognize(file, MailCatalog(), [], ["espinosa, diego"]);

        Assert.NotNull(result);
        Assert.Equal("Espinosa, Diego", result.Client);
        Assert.Equal("JARB LLC", result.Values["company"]);
        Assert.Equal("IRS Notice", result.Values["description"]);
    }

    [Fact]
    public void Accounting_names_split_the_agency_from_the_description_and_skip_an_empty_revoked()
    {
        var result = FilenameRecognizer.Recognize("Smith, John_FTB Notice_8-20-2026.pdf", WorkspaceCatalog.CreateDefault(), [],
            ["Smith, John"]);

        Assert.NotNull(result);
        Assert.Equal("Accounting", result.Workspace);
        Assert.Equal("Smith, John", result.Client);
        Assert.Equal("false", result.Values["revoked"]);
        Assert.Equal("FTB", result.Values["agency"]);
        Assert.Equal("Notice", result.Values["description"]);
        Assert.Equal("8-20-2026", result.Values["date"]);

        var revoked = FilenameRecognizer.Recognize("Smith, John_Revoked_IRS POA_1-05-2026.pdf", WorkspaceCatalog.CreateDefault(), [],
            ["Smith, John"]);
        Assert.Equal("true", revoked!.Values["revoked"]);
        Assert.Equal("IRS", revoked.Values["agency"]);
        Assert.Equal("1-05-2026", revoked.Values["date"]);
    }

    [Fact]
    public void Names_that_only_fit_by_guessing_are_not_filled_in()
    {
        // Any text fits "{client}_..." somehow; without a known client or a date/amount it is left alone.
        Assert.Null(FilenameRecognizer.Recognize("scan0001.pdf", MailCatalog(), [], []));
        Assert.Null(FilenameRecognizer.Recognize("Meeting notes_draft.pdf", MailCatalog(), [], []));
        Assert.Null(FilenameRecognizer.Recognize("2026.13.40 $10.98 Notice- Smith.pdf", MailCatalog(), [], []));
    }
}
