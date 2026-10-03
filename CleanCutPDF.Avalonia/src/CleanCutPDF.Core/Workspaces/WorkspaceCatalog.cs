namespace CleanCutPDF.Core.Workspaces;

public sealed class WorkspaceNote
{
    public string Id { get; set; } = Guid.NewGuid().ToString("N")[..8];
    public string Text { get; set; } = "";

    /// <summary>A field key, or "__top__" / "__end__".</summary>
    public string BeforeField { get; set; } = EndOfForm;

    public const string TopOfForm = "__top__";
    public const string EndOfForm = "__end__";
}

public sealed class WorkspaceDefinition
{
    public string Name { get; set; } = "";
    public string ClientLabel { get; set; } = "Client Name";
    public string Summary { get; set; } = "Custom document workflow.";
    public string FilenameTemplate { get; set; } = "{client}_{date}";
    public List<string> FieldKeys { get; set; } = [];
    public Dictionary<string, FieldOverride> FieldOverrides { get; set; } = new();
    public List<WorkspaceNote> Notes { get; set; } = [];
    public bool Permanent { get; set; }

    /// <summary>Custom form layout from the Layout Designer; null = automatic stacked form.</summary>
    public WorkspaceLayout? Layout { get; set; }
}

/// <summary>A workspace with its library fields merged with its overrides, ready to render.</summary>
public sealed record ResolvedWorkspace(
    string Name,
    string ClientLabel,
    string Summary,
    string FilenameTemplate,
    IReadOnlyList<FieldDefinition> Fields,
    IReadOnlyList<WorkspaceNote> Notes,
    WorkspaceLayout? Layout = null)
{
    public FieldDefinition? Field(string key) => Fields.FirstOrDefault(f => f.Key == key);
}

/// <summary>The field library plus every workspace. Defaults match CleanCutPDF 1.10.1.</summary>
public sealed class WorkspaceCatalog
{
    public const string AccountingName = "Accounting";

    public Dictionary<string, FieldDefinition> Fields { get; set; } = new();
    public List<WorkspaceDefinition> Workspaces { get; set; } = [];

    public IReadOnlyList<string> WorkspaceNames => Workspaces.Select(w => w.Name).ToList();

    public ResolvedWorkspace Resolve(string? name)
    {
        var definition = Workspaces.FirstOrDefault(w => w.Name == name)
                         ?? Workspaces.FirstOrDefault(w => w.Name == AccountingName)
                         ?? Workspaces[0];

        var fields = new List<FieldDefinition>();
        foreach (var key in definition.FieldKeys)
        {
            if (!Fields.TryGetValue(key, out var library))
            {
                continue;
            }

            var field = library.Clone();
            field.Key = key;
            if (definition.FieldOverrides.TryGetValue(key, out var o))
            {
                field.Default = o.Default ?? field.Default;
                field.Autofill = o.Autofill ?? field.Autofill;
                field.Required = o.Required ?? field.Required;
                field.Label = o.Label ?? field.Label;
            }

            fields.Add(field);
        }

        // The form gets its own copy, complete for exactly the fields it places.
        // Header fields stay in the Part header, exactly as in the automatic form.
        var layout = definition.Layout?.Clone();
        layout?.Sync(fields.Where(f => !f.IsHeaderField).Select(f => f.Key).ToList());

        return new ResolvedWorkspace(definition.Name, definition.ClientLabel, definition.Summary,
            definition.FilenameTemplate, fields, definition.Notes.ToList(), layout is { Tiles.Count: > 0 } ? layout : null);
    }

    /// <summary>The fields a custom layout places: every assigned field except those shown in the Part header.</summary>
    public IReadOnlyList<string> LayoutFieldKeys(WorkspaceDefinition workspace) =>
        workspace.FieldKeys.Where(key => Fields.TryGetValue(key, out var field) && !field.IsHeaderField).ToList();

    /// <summary>Repairs a loaded catalog: built-in fields restored, Accounting always present, dangling references removed.</summary>
    public void Normalize()
    {
        foreach (var (key, field) in CreateDefault().Fields)
        {
            Fields.TryAdd(key, field);
        }

        foreach (var (key, field) in Fields)
        {
            field.Key = key;
            if (!FieldDefinition.DateFormats.Contains(field.DateFormat))
            {
                field.DateFormat = FieldDefinition.DefaultDateFormat;
            }
        }

        if (Workspaces.All(w => w.Name != AccountingName))
        {
            Workspaces.Insert(0, CreateDefault().Workspaces.First(w => w.Name == AccountingName));
        }

        foreach (var workspace in Workspaces)
        {
            workspace.Permanent = workspace.Name == AccountingName || workspace.Permanent;
            workspace.FieldKeys = workspace.FieldKeys.Where(Fields.ContainsKey).Distinct().ToList();
            var validNotePositions = workspace.FieldKeys.Concat([WorkspaceNote.TopOfForm, WorkspaceNote.EndOfForm]).ToHashSet();
            workspace.Notes = workspace.Notes.Where(n => !string.IsNullOrWhiteSpace(n.Text)).ToList();
            foreach (var note in workspace.Notes.Where(n => !validNotePositions.Contains(n.BeforeField)))
            {
                note.BeforeField = WorkspaceNote.EndOfForm;
            }

            workspace.Layout?.Sync(LayoutFieldKeys(workspace));
            if (workspace.Layout is { Tiles.Count: 0 })
            {
                workspace.Layout = null;
            }
        }
    }

    public static WorkspaceCatalog CreateDefault()
    {
        var fields = new Dictionary<string, FieldDefinition>
        {
            ["revoked"] = new()
            {
                Key = "revoked", Label = "Revoked", Type = FieldType.Toggle, Placement = "header",
                Default = "false", Autofill = true, System = true
            },
            ["agency"] = new()
            {
                Key = "agency", Label = "Agency Code", Placeholder = "F", Autofill = true, System = true,
                Tooltip = "Agency Codes:\n• I = IRS\n• F = FTB\n• E = EDD\n• C = CDTFA\n• B = BOE"
            },
            ["description"] = new()
            {
                Key = "description", Label = "Description", Placeholder = "POA", Default = "POA",
                Autofill = true, TitleCase = true, System = true
            },
            ["date"] = new()
            {
                Key = "date", Label = "Date", Type = FieldType.Date, Placeholder = "e.g. 8-20-2026",
                Autofill = true, DateFormat = "M-D-YYYY", System = true
            },
            ["matter_number"] = new()
            {
                Key = "matter_number", Label = "Matter / Case #", Placeholder = "Matter or case number",
                Autofill = true, System = true
            },
            ["document_type"] = new()
            {
                Key = "document_type", Label = "Document Type", Placeholder = "e.g. Notice, Letter, Filing",
                Autofill = true, TitleCase = true, System = true
            },
            ["amount"] = new()
            {
                Key = "amount", Label = "Amount", Type = FieldType.Currency, Placeholder = "e.g. 134.06", System = true
            },
            ["payment_method"] = new()
            {
                Key = "payment_method", Label = "Payment Method", Type = FieldType.Choice,
                Options = ["ACH", "CC", "CK", "Other"], System = true
            },
            ["check_number"] = new()
            {
                Key = "check_number", Label = "Check Number", Placeholder = "e.g. 1234", System = true,
                Condition = new FieldCondition { Field = "payment_method", EqualsValue = "CK" }
            },
            ["company"] = new()
            {
                Key = "company", Label = "Company", Type = FieldType.Choice,
                Options = ["JARB", "AB INC", "JL APC", "JARB LLC", "Other"], System = true
            }
        };

        var workspaces = new List<WorkspaceDefinition>
        {
            new()
            {
                Name = AccountingName,
                ClientLabel = "Client Name",
                Summary = "Accounting and tax-document workflow with agency, revoked status, description, and date.",
                FilenameTemplate = "{client}_{revoked}_{agency_description}_{date}",
                FieldKeys = ["revoked", "agency", "description", "date"],
                FieldOverrides = { ["description"] = new FieldOverride { Default = "POA", Autofill = true } },
                Permanent = true
            },
            new()
            {
                Name = "Legal",
                ClientLabel = "Client / Matter Name",
                Summary = "Legal workflow with matter/case number, document type, description, and document date.",
                FilenameTemplate = "{client}_{matter_number}_{document_type}_{description}_{date}",
                FieldKeys = ["matter_number", "document_type", "description", "date"],
                FieldOverrides = { ["description"] = new FieldOverride { Default = "", Autofill = true } }
            }
        };

        return new WorkspaceCatalog { Fields = fields, Workspaces = workspaces };
    }
}
