using CleanCutPDF.App.ViewModels.Editor;
using CleanCutPDF.Core.Pdf;
using CleanCutPDF.Core.Workspaces;

namespace CleanCutPDF.App.Tests;

public sealed class WorkspaceFormTests
{
    private static readonly DateOnly Today = new(2026, 10, 2);
    private static readonly PageRange[] ThreeParts = [new(0, 1), new(3, 3), new(5, 7)];

    private static WorkspaceFormViewModel Accounting(IReadOnlyList<Dictionary<string, string>>? saved = null) =>
        new(WorkspaceCatalog.CreateDefault().Resolve("Accounting"), ThreeParts, saved, _ => { }, Today);

    private static WorkspaceFormViewModel Deposits()
    {
        var catalog = WorkspaceCatalog.CreateDefault();
        catalog.Workspaces.Add(new WorkspaceDefinition
        {
            Name = "Deposits",
            FieldKeys = ["payment_method", "check_number", "amount", "company"],
            Notes = [new WorkspaceNote { Text = "Staple the check copy.", BeforeField = "check_number" },
                     new WorkspaceNote { Text = "Top reminder", BeforeField = WorkspaceNote.TopOfForm }]
        });
        return new WorkspaceFormViewModel(catalog.Resolve("Deposits"), ThreeParts, null, _ => { }, Today);
    }

    private static string V(WorkspaceFormViewModel form, int part, string key) => form.Parts[part].Field(key)!.Value;

    [Fact]
    public void Defaults_and_header_fields()
    {
        var form = Accounting();

        Assert.Equal("POA", V(form, 2, "description"));
        Assert.Equal("false", V(form, 0, "revoked"));
        Assert.Equal(["revoked"], form.Parts[0].HeaderFields.Select(f => f.Key));
        Assert.Equal("Part 2 — Pages 4 to 4", form.Parts[1].Title);
    }

    [Fact]
    public void Autofill_carries_values_forward_until_a_part_is_edited_by_hand()
    {
        var form = Accounting();

        form.Parts[0].Field("agency")!.Value = "i";
        Assert.Equal("i", V(form, 1, "agency"));
        Assert.Equal("i", V(form, 2, "agency"));

        form.Parts[1].Field("agency")!.Value = "f"; // manual edit in Part 2 (Part 3 follows it)
        Assert.Equal("f", V(form, 2, "agency"));

        form.Parts[0].Field("agency")!.Value = "e"; // Part 2 was edited by hand, so it stays
        Assert.Equal("f", V(form, 1, "agency"));
        Assert.Equal("f", V(form, 2, "agency"));
    }

    [Fact]
    public void Typing_character_by_character_carries_forward()
    {
        var form = Accounting();
        var date = form.Parts[0].Field("date")!;

        foreach (var text in new[] { "0", "08", "082", "0820", "08202", "082026" })
        {
            date.Value = text;
        }

        Assert.Equal("082026", V(form, 2, "date"));
    }

    [Fact]
    public void Toggles_carry_forward_too()
    {
        var form = Accounting();
        ((BooleanFieldViewModel)form.Parts[0].Field("revoked")!).IsChecked = true;
        Assert.Equal("true", V(form, 2, "revoked"));
    }

    [Fact]
    public void Check_number_only_shows_for_checks_and_other_shows_free_text()
    {
        var form = Deposits();
        var part = form.Parts[0];
        var method = (ChoiceFieldViewModel)part.Field("payment_method")!;
        var check = part.Field("check_number")!;

        Assert.Equal("Select...", method.SelectedOption);
        Assert.False(check.IsVisible);

        method.SelectedOption = "CK";
        Assert.True(check.IsVisible);
        Assert.Equal("CK", method.Value);

        method.SelectedOption = "Other";
        Assert.True(method.ShowOther);
        method.OtherText = "Wire";
        Assert.Equal("Wire", method.Value);
        Assert.False(check.IsVisible);
        Assert.Equal(["Staple the check copy."], check.Notes);
        Assert.Equal(["Top reminder"], part.TopNotes);
    }

    [Fact]
    public void Saved_choice_values_restore_into_the_right_controls()
    {
        var catalog = WorkspaceCatalog.CreateDefault();
        catalog.Workspaces.Add(new WorkspaceDefinition { Name = "D", FieldKeys = ["payment_method", "company"] });
        var saved = new List<Dictionary<string, string>> { new() { ["payment_method"] = "Zelle", ["company"] = "JARB" } };

        var form = new WorkspaceFormViewModel(catalog.Resolve("D"), [new PageRange(0, 0)], saved, _ => { }, Today);
        var method = (ChoiceFieldViewModel)form.Parts[0].Field("payment_method")!;
        var company = (ChoiceFieldViewModel)form.Parts[0].Field("company")!;

        Assert.Equal("Other", method.SelectedOption);
        Assert.Equal("Zelle", method.OtherText);
        Assert.Equal("JARB", company.SelectedOption);
    }

    [Fact]
    public void Currency_normalizes_and_invalid_text_is_left_for_export_to_explain()
    {
        var amount = (TextFieldViewModel)Deposits().Parts[0].Field("amount")!;

        amount.Text = "1234.5";
        amount.Normalize();
        Assert.Equal("$1,234.50", amount.Text);

        amount.Text = "twelve";
        amount.Normalize();
        Assert.Equal("twelve", amount.Text);
    }

    [Fact]
    public void Capture_restore_and_reset()
    {
        var form = Accounting();
        form.Parts[0].Field("agency")!.Value = "i";
        form.Parts[2].Field("description")!.Value = "Notice";

        var restored = Accounting(form.Capture());
        Assert.Equal("i", V(restored, 1, "agency"));
        Assert.Equal("Notice", V(restored, 2, "description"));

        restored.Reset();
        Assert.Equal("", V(restored, 1, "agency"));
        Assert.Equal("POA", V(restored, 2, "description"));
    }

    [Fact]
    public void Auto_today_date_fields_start_with_today()
    {
        var catalog = WorkspaceCatalog.CreateDefault();
        catalog.Fields["date"].AutoToday = true;
        var form = new WorkspaceFormViewModel(catalog.Resolve("Accounting"), ThreeParts, null, _ => { }, Today);

        Assert.Equal("10-02-2026", V(form, 0, "date"));
    }

    [Fact]
    public void Part_title_jumps_the_preview_to_its_first_page()
    {
        var jumped = -1;
        var form = new WorkspaceFormViewModel(WorkspaceCatalog.CreateDefault().Resolve("Accounting"), ThreeParts, null,
            page => jumped = page, Today);

        form.Parts[2].ShowInPreviewCommand.Execute(null);

        Assert.Equal(5, jumped);
    }
}
