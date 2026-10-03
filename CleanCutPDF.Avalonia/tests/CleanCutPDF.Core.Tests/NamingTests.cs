using CleanCutPDF.Core.Naming;
using CleanCutPDF.Core.Workspaces;

namespace CleanCutPDF.Core.Tests;

public sealed class NamingTests
{
    private static readonly WorkspaceCatalog Catalog = WorkspaceCatalog.CreateDefault();

    [Theory]
    [InlineData("082026", 2026, 8, 20)]
    [InlineData("82026", 2026, 8, 20)]
    [InlineData("08202026", 2026, 8, 20)]
    [InlineData("8-20-2026", 2026, 8, 20)]
    [InlineData("08/20/2026", 2026, 8, 20)]
    [InlineData("2026.08.20", 2026, 8, 20)]
    [InlineData("2026-8-2", 2026, 8, 2)]
    [InlineData(" 010170 ", 1970, 1, 1)] // Python %y: 69-99 → 1900s
    [InlineData("010168", 2068, 1, 1)]
    public void Flexible_dates_parse(string input, int y, int m, int d) =>
        Assert.Equal(new DateOnly(y, m, d), DateFieldFormat.Parse(input));

    [Theory]
    [InlineData("")]
    [InlineData("023026")] // Feb 30
    [InlineData("13-01-2026")]
    [InlineData("8-20/2026")]
    [InlineData("hello")]
    public void Invalid_dates_are_rejected(string input) =>
        Assert.False(DateFieldFormat.TryParse(input, out _));

    [Theory]
    [InlineData("M-D-YYYY", "8-05-2026")] // 1.x pads the day but not the month
    [InlineData("MM-DD-YYYY", "08-05-2026")]
    [InlineData("YYYY.MM.DD", "2026.08.05")]
    [InlineData("MMDDYY", "080526")]
    [InlineData(null, "8-05-2026")]
    public void Dates_format_per_field(string? format, string expected) =>
        Assert.Equal(expected, DateFieldFormat.Format(new DateOnly(2026, 8, 5), format));

    [Theory]
    [InlineData("134.06", "$134.06")]
    [InlineData("1234.5", "$1,234.50")]
    [InlineData("$1,234.50 USD", "$1,234.50")]
    [InlineData("2.345", "$2.34")] // banker's rounding like Python Decimal
    [InlineData("2.355", "$2.36")]
    [InlineData("", "")]
    public void Currency_formats(string input, string expected) =>
        Assert.Equal(expected, CurrencyFormat.Format(input));

    [Fact]
    public void Invalid_currency_has_friendly_message() =>
        Assert.Equal(CurrencyFormat.InvalidMessage,
            Assert.Throws<FormatException>(() => CurrencyFormat.Format("12 dollars")).Message);

    [Theory]
    [InlineData("john smith", "John Smith")]
    [InlineData("acme llc", "Acme LLC")]
    [InlineData("mary-jane o'brien", "Mary-Jane O'Brien")]
    [InlineData("mcdonald", "McDonald")]
    [InlineData("JOHN SMITH", "JOHN SMITH")] // already-capitalized words are preserved (use Aa to normalize)
    [InlineData("MacDonald", "MacDonald")]
    [InlineData("machado", "Machado")] // 1.x produced "MacHado"
    [InlineData("  spaced   out  ", "Spaced Out")]
    [InlineData("poa", "POA")]
    public void Title_case(string input, string expected) =>
        Assert.Equal(expected, NameCasing.TitleCase(input));

    [Theory]
    [InlineData("i", "IRS")]
    [InlineData("F", "FTB")]
    [InlineData(" e ", "EDD")]
    [InlineData("c", "CDTFA")]
    [InlineData("b", "BOE")]
    [InlineData("ssa", "SSA")]
    public void Agency_codes_expand(string code, string expected) =>
        Assert.Equal(expected, AgencyCodes.Expand(code));

    [Fact]
    public void Accounting_filename_matches_1x()
    {
        var workspace = Catalog.Resolve("Accounting");
        var values = new PartValues { ["revoked"] = "true", ["agency"] = "i", ["description"] = "poa", ["date"] = "082026" };

        var tokens = FilenameBuilder.BuildTokens(workspace, "John Smith", values);

        Assert.Equal("IRS POA", tokens["agency_description"]);
        Assert.Equal("John Smith_Revoked_IRS POA_8-20-2026", FilenameBuilder.Render(workspace.FilenameTemplate, tokens));
    }

    [Fact]
    public void Blank_parts_collapse_cleanly()
    {
        var workspace = Catalog.Resolve("Accounting");
        var values = new PartValues { ["revoked"] = "false", ["agency"] = "", ["description"] = "inv", ["date"] = "" };

        var name = FilenameBuilder.Render(workspace.FilenameTemplate, FilenameBuilder.BuildTokens(workspace, "", values));

        Assert.Equal("Invoice", name); // client optional; "inv" → "Invoice"
    }

    [Fact]
    public void Inv_is_only_replaced_as_a_whole_word()
    {
        var workspace = Catalog.Resolve("Accounting");
        var tokens = FilenameBuilder.BuildTokens(workspace, "A",
            new PartValues { ["description"] = "inventory inv list" });
        Assert.Equal("Inventory Invoice List", tokens["description"]);
    }

    [Fact]
    public void Check_number_only_appears_for_checks()
    {
        var catalog = WorkspaceCatalog.CreateDefault();
        catalog.Workspaces.Add(new WorkspaceDefinition
        {
            Name = "Deposits",
            FilenameTemplate = "{client}_{payment_method}{check_number}_{amount}",
            FieldKeys = ["payment_method", "check_number", "amount"]
        });
        var workspace = catalog.Resolve("Deposits");

        string Name(string method) => FilenameBuilder.Render(workspace.FilenameTemplate,
            FilenameBuilder.BuildTokens(workspace, "Acme",
                new PartValues { ["payment_method"] = method, ["check_number"] = "1234", ["amount"] = "50" }));

        Assert.Equal("Acme_CK 1234_$50.00", Name("CK"));
        Assert.Equal("Acme_ACH_$50.00", Name("ACH"));
    }

    [Fact]
    public void Invalid_date_reports_the_field_problem()
    {
        var workspace = Catalog.Resolve("Accounting");
        var error = Assert.Throws<FormatException>(() =>
            FilenameBuilder.BuildTokens(workspace, "A", new PartValues { ["date"] = "13/45/2026" }));
        Assert.Equal(DateFieldFormat.InvalidMessage, error.Message);
    }

    [Theory]
    [InlineData("a<b>c:d\"e/f\\g|h?i*j", "a_b_c_d_e_f_g_h_i_j")]
    [InlineData("Client _ Name", "Client_ Name")]
    [InlineData("__lead__trail__", "lead_trail")]
    [InlineData("name. ", "name")]
    [InlineData("con", "_con")]
    [InlineData("", "Document")]
    public void Sanitize_matches_1x(string input, string expected) =>
        Assert.Equal(expected, FilenameBuilder.Sanitize(input));

    [Fact]
    public void Unknown_tokens_render_empty() =>
        Assert.Equal("A", FilenameBuilder.Render("{client}_{nope}", new Dictionary<string, string> { ["client"] = "A" }));

    [Fact]
    public void Default_catalog_matches_1x_workspaces()
    {
        Assert.Equal(["Accounting", "Legal"], Catalog.WorkspaceNames);
        var accounting = Catalog.Resolve("Accounting");
        Assert.Equal(["revoked", "agency", "description", "date"], accounting.Fields.Select(f => f.Key));
        Assert.Equal("POA", accounting.Field("description")!.Default);
        Assert.True(accounting.Field("revoked")!.IsHeaderField);
        Assert.Equal("", Catalog.Resolve("Legal").Field("description")!.Default);
        Assert.Equal("Accounting", Catalog.Resolve("does not exist").Name);
    }

    [Fact]
    public void Auto_today_fills_blank_date_in_field_format()
    {
        var field = new FieldDefinition { Type = FieldType.Date, AutoToday = true, DateFormat = "YYYY.MM.DD" };
        Assert.Equal("2026.10.02", FieldRules.InitialValue(field, new DateOnly(2026, 10, 2)));
    }
}
