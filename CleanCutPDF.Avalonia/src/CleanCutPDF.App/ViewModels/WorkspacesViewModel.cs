using System.Collections.ObjectModel;
using CleanCutPDF.App.Services;
using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Naming;
using CleanCutPDF.Core.Services;
using CleanCutPDF.Core.Sessions;
using CleanCutPDF.Core.Workspaces;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace CleanCutPDF.App.ViewModels;

public sealed class FieldRow(string key, string label, string typeLabel, bool isBuiltIn) : ObservableObject
{
    public string Key { get; } = key;
    public string Label { get; private set; } = label;
    public string TypeLabel { get; private set; } = typeLabel;
    public bool IsBuiltIn { get; } = isBuiltIn;
    public string Display => $"{Label}  ·  {TypeLabel}{(IsBuiltIn ? "  ·  built-in" : "")}";

    /// <summary>Updates the text in place so list selection is kept while editing.</summary>
    public void Update(string label, string typeLabel)
    {
        Label = label;
        TypeLabel = typeLabel;
        OnPropertyChanged(nameof(Label));
        OnPropertyChanged(nameof(Display));
    }

    public override string ToString() => Display;
}

public sealed record NoteRow(WorkspaceNote Note, string Position)
{
    public string Display => $"{Position}: {Note.Text}";
    public override string ToString() => Display;
}

public sealed record TokenButton(string Token, string Label);

/// <summary>
/// Workspaces &amp; Fields editor (the 1.x Settings › Workspaces and Custom Fields
/// screens). Every change is saved automatically a moment after it is made,
/// and open editors pick it up immediately.
/// </summary>
public sealed partial class WorkspacesViewModel : ObservableObject
{
    public static readonly IReadOnlyDictionary<FieldType, string> TypeLabels = new Dictionary<FieldType, string>
    {
        [FieldType.Text] = "Text",
        [FieldType.Number] = "Number",
        [FieldType.Currency] = "Currency",
        [FieldType.Date] = "Date",
        [FieldType.Choice] = "Dropdown / Choice",
        [FieldType.Checkbox] = "Checkbox",
        [FieldType.Toggle] = "Toggle"
    };

    private readonly WorkspaceStore _store;
    private readonly DocumentStore _documents;
    private readonly ISettingsService _settings;
    private readonly IDialogService _dialogs;
    private readonly CrashLog _crashLog;
    private readonly AppLog _log;
    private CancellationTokenSource? _pendingSave;
    private bool _ownSave;
    private bool _loading;

    public WorkspacesViewModel(WorkspaceStore store, DocumentStore documents, ISettingsService settings,
        IDialogService dialogs, CrashLog crashLog, AppLog log)
    {
        _store = store;
        _documents = documents;
        _settings = settings;
        _dialogs = dialogs;
        _crashLog = crashLog;
        _log = log;
        _store.Changed += (_, _) =>
        {
            // Reload only for changes made elsewhere (e.g. the 1.x import), never for our own
            // saves, so typing is not interrupted.
            if (!_ownSave && _pendingSave is null)
            {
                Reload(SelectedWorkspaceName, SelectedLibraryField?.Key);
            }
        };
        Reload(null, null);
    }

    private WorkspaceCatalog Catalog => _store.Catalog;

    private WorkspaceDefinition? Current =>
        Catalog.Workspaces.FirstOrDefault(w => w.Name == SelectedWorkspaceName);

    // ───── Workspace list ─────

    public ObservableCollection<string> WorkspaceNames { get; } = [];

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(RenameWorkspaceCommand), nameof(DeleteWorkspaceCommand))]
    public partial string? SelectedWorkspaceName { get; set; }

    public bool IsPermanent => Current?.Permanent == true;

    [ObservableProperty]
    public partial string SaveStatus { get; private set; } = "All changes saved";

    // ───── Workspace details ─────

    [ObservableProperty]
    public partial string ClientLabel { get; set; } = "";

    [ObservableProperty]
    public partial string Summary { get; set; } = "";

    [ObservableProperty]
    public partial string FilenameTemplate { get; set; } = "";

    [ObservableProperty]
    public partial string FilenamePreview { get; private set; } = "";

    public ObservableCollection<TokenButton> Tokens { get; } = [];

    public ObservableCollection<FieldRow> AssignedFields { get; } = [];

    public ObservableCollection<FieldRow> AvailableFields { get; } = [];

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(HasAssignedSelection))]
    public partial FieldRow? SelectedAssigned { get; set; }

    [ObservableProperty]
    public partial FieldRow? SelectedAvailable { get; set; }

    public bool HasAssignedSelection => SelectedAssigned is not null;

    /// <summary>Default value for the selected field in this workspace only (e.g. Description = POA in Accounting).</summary>
    [ObservableProperty]
    public partial string WorkspaceDefault { get; set; } = "";

    public ObservableCollection<NoteRow> Notes { get; } = [];

    [ObservableProperty]
    public partial NoteRow? SelectedNote { get; set; }

    // ───── Field library ─────

    public ObservableCollection<FieldRow> LibraryFields { get; } = [];

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(DeleteFieldCommand))]
    public partial FieldRow? SelectedLibraryField { get; set; }

    [ObservableProperty]
    public partial FieldEditorViewModel? FieldEditor { get; private set; }

    // ───── Loading ─────

    private void Reload(string? workspaceName, string? fieldKey)
    {
        _loading = true;
        try
        {
            WorkspaceNames.Clear();
            foreach (var name in Catalog.WorkspaceNames)
            {
                WorkspaceNames.Add(name);
            }

            LibraryFields.Clear();
            foreach (var field in Catalog.Fields.Values.OrderBy(f => !f.System).ThenBy(f => f.Label))
            {
                LibraryFields.Add(Row(field));
            }
        }
        finally
        {
            _loading = false;
        }

        SelectedWorkspaceName = WorkspaceNames.Contains(workspaceName ?? "") ? workspaceName : WorkspaceNames.FirstOrDefault();
        SelectedLibraryField = LibraryFields.FirstOrDefault(f => f.Key == fieldKey) ?? LibraryFields.FirstOrDefault();
        LoadWorkspace();
    }

    partial void OnSelectedWorkspaceNameChanged(string? value)
    {
        if (!_loading)
        {
            LoadWorkspace();
        }
    }

    private void LoadWorkspace()
    {
        var workspace = Current;
        _loading = true;
        try
        {
            ClientLabel = workspace?.ClientLabel ?? "";
            Summary = workspace?.Summary ?? "";
            FilenameTemplate = workspace?.FilenameTemplate ?? "";
            RefreshFieldLists();
            RefreshNotes();
            RefreshTokens();
        }
        finally
        {
            _loading = false;
        }

        OnPropertyChanged(nameof(IsPermanent));
        RefreshLayoutStatus();
        UpdatePreview();
    }

    private void RefreshFieldLists(string? keepAssigned = null)
    {
        var workspace = Current;
        AssignedFields.Clear();
        AvailableFields.Clear();
        if (workspace is null)
        {
            return;
        }

        foreach (var key in workspace.FieldKeys)
        {
            if (Catalog.Fields.TryGetValue(key, out var field))
            {
                AssignedFields.Add(Row(field));
            }
        }

        foreach (var field in Catalog.Fields.Values.Where(f => !workspace.FieldKeys.Contains(f.Key)).OrderBy(f => f.Label))
        {
            AvailableFields.Add(Row(field));
        }

        SelectedAssigned = AssignedFields.FirstOrDefault(f => f.Key == keepAssigned);
    }

    private void RefreshNotes()
    {
        Notes.Clear();
        foreach (var note in Current?.Notes ?? [])
        {
            Notes.Add(new NoteRow(note, PositionLabel(note.BeforeField)));
        }
    }

    private void RefreshTokens()
    {
        Tokens.Clear();
        if (Current is { } workspace)
        {
            foreach (var (token, label) in Catalog.FilenameTokens(workspace.Name))
            {
                Tokens.Add(new TokenButton(token, label));
            }
        }
    }

    // ───── Workspace commands ─────

    [RelayCommand]
    private async Task NewWorkspaceAsync()
    {
        var name = await _dialogs.PromptAsync("New Workspace", "Workspace name:", "", "Create");
        if (string.IsNullOrWhiteSpace(name))
        {
            return;
        }

        if (await TryEditAsync(() => Catalog.AddWorkspace(name)))
        {
            Reload(name.Trim(), SelectedLibraryField?.Key);
            ScheduleSave($"Created workspace {name.Trim()}");
        }
    }

    [RelayCommand(CanExecute = nameof(CanChangeWorkspace))]
    private async Task RenameWorkspaceAsync()
    {
        if (SelectedWorkspaceName is not { } oldName)
        {
            return;
        }

        var newName = await _dialogs.PromptAsync("Rename Workspace", "New workspace name:", oldName, "Rename");
        if (string.IsNullOrWhiteSpace(newName) || newName.Trim() == oldName)
        {
            return;
        }

        newName = newName.Trim();
        _documents.CaptureEditor();
        if (!await TryEditAsync(() => Catalog.RenameWorkspace(oldName, newName)))
        {
            return;
        }

        // Keep open PDFs and their typed values pointing at the renamed workspace.
        foreach (var document in _documents.Documents)
        {
            if (document.WorkspaceData.Remove(oldName, out var rows))
            {
                document.WorkspaceData[newName] = rows;
            }

            if (document.Workspace == oldName)
            {
                document.Workspace = newName;
            }
        }

        if (_settings.Current.DefaultWorkspace == oldName)
        {
            _settings.Update(s => s.DefaultWorkspace = newName);
        }

        _documents.RequestSave();
        Reload(newName, SelectedLibraryField?.Key);
        ScheduleSave($"Renamed workspace {oldName} → {newName}");
    }

    [RelayCommand(CanExecute = nameof(CanChangeWorkspace))]
    private async Task DeleteWorkspaceAsync()
    {
        if (SelectedWorkspaceName is not { } name ||
            !await _dialogs.ConfirmAsync("Delete Workspace",
                $"Delete the “{name}” workspace?\n\nOpen PDFs that use it will switch to Accounting. Your PDF files are not affected.",
                "Delete"))
        {
            return;
        }

        _documents.CaptureEditor();
        if (!await TryEditAsync(() => Catalog.DeleteWorkspace(name)))
        {
            return;
        }

        foreach (var document in _documents.Documents)
        {
            document.WorkspaceData.Remove(name);
            if (document.Workspace == name)
            {
                document.Workspace = WorkspaceCatalog.AccountingName;
            }
        }

        if (_settings.Current.DefaultWorkspace == name)
        {
            _settings.Update(s => s.DefaultWorkspace = WorkspaceCatalog.AccountingName);
        }

        _documents.RequestSave();
        Reload(WorkspaceCatalog.AccountingName, SelectedLibraryField?.Key);
        ScheduleSave($"Deleted workspace {name}");
    }

    private bool CanChangeWorkspace() =>
        SelectedWorkspaceName is not null && SelectedWorkspaceName != WorkspaceCatalog.AccountingName && !IsPermanent;

    partial void OnClientLabelChanged(string value) => EditCurrent(w => w.ClientLabel = value.Trim().Length > 0 ? value.Trim() : "Client Name");
    partial void OnSummaryChanged(string value) => EditCurrent(w => w.Summary = value);

    partial void OnFilenameTemplateChanged(string value)
    {
        EditCurrent(w => w.FilenameTemplate = value.Trim().Length > 0 ? value.Trim() : "{client}_{date}");
        UpdatePreview();
    }

    [RelayCommand]
    private void InsertToken(TokenButton? token)
    {
        if (token is null)
        {
            return;
        }

        var template = FilenameTemplate.TrimEnd();
        var separator = template.Length == 0 || template.EndsWith('_') || template.EndsWith(' ') || template.EndsWith('-') ? "" : "_";
        FilenameTemplate = template + separator + "{" + token.Token + "}";
    }

    // ───── Field assignment ─────

    [RelayCommand]
    private void AssignField()
    {
        if (SelectedAvailable is not { } row || Current is not { } workspace)
        {
            return;
        }

        workspace.AssignField(row.Key);
        AfterFieldsChanged(row.Key, $"Added {row.Label} to {workspace.Name}");
    }

    [RelayCommand]
    private void UnassignField()
    {
        if (SelectedAssigned is not { } row || Current is not { } workspace)
        {
            return;
        }

        workspace.UnassignField(row.Key);
        RefreshNotes();
        AfterFieldsChanged(null, $"Removed {row.Label} from {workspace.Name}");
    }

    [RelayCommand]
    private void MoveFieldUp() => MoveField(-1);

    [RelayCommand]
    private void MoveFieldDown() => MoveField(+1);

    private void MoveField(int direction)
    {
        if (SelectedAssigned is not { } row || Current is not { } workspace)
        {
            return;
        }

        workspace.MoveField(row.Key, direction);
        AfterFieldsChanged(row.Key, $"Reordered fields in {workspace.Name}");
    }

    partial void OnSelectedAssignedChanged(FieldRow? value)
    {
        _loading = true;
        WorkspaceDefault = value is not null && Current is { } workspace
            ? workspace.FieldOverrides.TryGetValue(value.Key, out var o) && o.Default is not null
                ? o.Default
                : Catalog.Fields.TryGetValue(value.Key, out var field) ? field.Default : ""
            : "";
        _loading = false;
    }

    partial void OnWorkspaceDefaultChanged(string value)
    {
        if (_loading || SelectedAssigned is not { } row || Current is not { } workspace)
        {
            return;
        }

        var library = Catalog.Fields.TryGetValue(row.Key, out var field) ? field.Default : "";
        if (value == library)
        {
            if (workspace.FieldOverrides.TryGetValue(row.Key, out var existing))
            {
                existing.Default = null;
            }
        }
        else
        {
            if (!workspace.FieldOverrides.TryGetValue(row.Key, out var o))
            {
                workspace.FieldOverrides[row.Key] = o = new FieldOverride();
            }

            o.Default = value;
        }

        UpdatePreview();
        ScheduleSave($"{workspace.Name}: default for {row.Label} changed");
    }

    private void AfterFieldsChanged(string? keepSelected, string message)
    {
        RefreshFieldLists(keepSelected);
        RefreshTokens();
        UpdatePreview();
        ScheduleSave(message);
    }

    // ───── Form layout ─────

    public bool HasCustomLayout => Current?.Layout is not null;

    public string LayoutStatus => HasCustomLayout
        ? "Custom layout active"
        : "Automatic layout (fields stacked in order)";

    [RelayCommand]
    private async Task DesignLayoutAsync()
    {
        if (Current is not { } workspace)
        {
            return;
        }

        var resolved = Catalog.Resolve(workspace.Name);
        if (resolved.Fields.All(f => f.IsHeaderField))
        {
            await _dialogs.ShowMessageAsync("Layout Designer",
                "Add at least one field to this workspace first (fields shown in the Part header are not part of the layout).");
            return;
        }

        var designer = new LayoutDesignerViewModel(resolved, workspace.Layout);
        if (!await _dialogs.ShowLayoutDesignerAsync(designer))
        {
            return;
        }

        // Saving the designer untouched (or back in one column) keeps the automatic form.
        var layout = designer.Result();
        if (layout is null && workspace.Layout is null)
        {
            return;
        }

        workspace.Layout = layout;
        RefreshLayoutStatus();
        ScheduleSave(layout is null ? $"{workspace.Name}: back to the automatic layout" : $"{workspace.Name}: custom layout saved");
    }

    /// <summary>1.x "Reset Layout": back to the automatic stacked form.</summary>
    [RelayCommand(CanExecute = nameof(HasCustomLayout))]
    private async Task UseAutomaticLayoutAsync()
    {
        if (Current is not { Layout: not null } workspace ||
            !await _dialogs.ConfirmAsync("Automatic Layout",
                $"Remove the custom layout for “{workspace.Name}” and stack its fields in order again?", "Use Automatic Layout"))
        {
            return;
        }

        workspace.Layout = null;
        RefreshLayoutStatus();
        ScheduleSave($"{workspace.Name}: custom layout removed");
    }

    private void RefreshLayoutStatus()
    {
        OnPropertyChanged(nameof(HasCustomLayout));
        OnPropertyChanged(nameof(LayoutStatus));
        UseAutomaticLayoutCommand.NotifyCanExecuteChanged();
    }

    // ───── Notes ─────

    private IReadOnlyList<(string Key, string Label)> NotePositions() =>
        [
            (WorkspaceNote.TopOfForm, "Top of each Part"),
            .. (Current?.FieldKeys ?? []).Where(Catalog.Fields.ContainsKey).Select(k => (k, $"Under {Catalog.Fields[k].Label}")),
            (WorkspaceNote.EndOfForm, "End of each Part")
        ];

    private string PositionLabel(string key) =>
        NotePositions().FirstOrDefault(p => p.Key == key).Label ?? "End of each Part";

    [RelayCommand]
    private async Task AddNoteAsync()
    {
        if (Current is not { } workspace)
        {
            return;
        }

        var text = await _dialogs.PromptAsync("Add Note", "Reminder text shown in the form:", "", "Next");
        if (string.IsNullOrWhiteSpace(text))
        {
            return;
        }

        var positions = NotePositions();
        var chosen = await _dialogs.ChooseAsync("Add Note", "Where should it appear?",
            positions.Select(p => p.Label).ToList(), positions[^1].Label, "Add");
        if (chosen is null)
        {
            return;
        }

        workspace.Notes.Add(new WorkspaceNote { Text = text.Trim(), BeforeField = positions.First(p => p.Label == chosen).Key });
        RefreshNotes();
        ScheduleSave($"{workspace.Name}: note added");
    }

    [RelayCommand]
    private async Task EditNoteAsync()
    {
        if (SelectedNote is not { } row || Current is not { } workspace)
        {
            return;
        }

        var text = await _dialogs.PromptAsync("Edit Note", "Reminder text:", row.Note.Text, "Next");
        if (string.IsNullOrWhiteSpace(text))
        {
            return;
        }

        var positions = NotePositions();
        var chosen = await _dialogs.ChooseAsync("Edit Note", "Where should it appear?",
            positions.Select(p => p.Label).ToList(), PositionLabel(row.Note.BeforeField), "Save");
        if (chosen is null)
        {
            return;
        }

        row.Note.Text = text.Trim();
        row.Note.BeforeField = positions.First(p => p.Label == chosen).Key;
        RefreshNotes();
        ScheduleSave($"{workspace.Name}: note edited");
    }

    [RelayCommand]
    private void RemoveNote()
    {
        if (SelectedNote is not { } row || Current is not { } workspace)
        {
            return;
        }

        workspace.Notes.Remove(row.Note);
        RefreshNotes();
        ScheduleSave($"{workspace.Name}: note removed");
    }

    // ───── Field library ─────

    partial void OnSelectedLibraryFieldChanged(FieldRow? value)
    {
        FieldEditor = value is not null && Catalog.Fields.TryGetValue(value.Key, out var field)
            ? new FieldEditorViewModel(field, Catalog, () =>
            {
                value.Update(field.Label, TypeLabels.GetValueOrDefault(field.Type, "Text"));
                RefreshFieldLists(SelectedAssigned?.Key);
                RefreshTokens();
                UpdatePreview();
                ScheduleSave($"Field {field.Label} changed");
            })
            : null;
    }

    [RelayCommand]
    private async Task NewFieldAsync()
    {
        var label = await _dialogs.PromptAsync("New Custom Field", "Field name:", "", "Create");
        if (string.IsNullOrWhiteSpace(label))
        {
            return;
        }

        FieldDefinition? field = null;
        if (await TryEditAsync(() => field = Catalog.AddField(label)) && field is not null)
        {
            Reload(SelectedWorkspaceName, field.Key);
            ScheduleSave($"Created field {field.Label}");
        }
    }

    [RelayCommand(CanExecute = nameof(CanDeleteField))]
    private async Task DeleteFieldAsync()
    {
        if (SelectedLibraryField is not { } row ||
            !await _dialogs.ConfirmAsync("Delete Field",
                $"Delete the “{row.Label}” field? It will be removed from every workspace.", "Delete"))
        {
            return;
        }

        if (await TryEditAsync(() => Catalog.DeleteField(row.Key)))
        {
            Reload(SelectedWorkspaceName, null);
            ScheduleSave($"Deleted field {row.Label}");
        }
    }

    private bool CanDeleteField() => SelectedLibraryField is { IsBuiltIn: false };

    // ───── Helpers ─────

    private void EditCurrent(Action<WorkspaceDefinition> change)
    {
        if (_loading || Current is not { } workspace)
        {
            return;
        }

        change(workspace);
        ScheduleSave($"{workspace.Name} updated");
    }

    private async Task<bool> TryEditAsync(Action edit)
    {
        try
        {
            edit();
            return true;
        }
        catch (WorkspaceEditException error)
        {
            await _dialogs.ShowMessageAsync("Workspaces", error.Message);
            return false;
        }
    }

    private void UpdatePreview()
    {
        if (Current is not { } workspace)
        {
            FilenamePreview = "";
            return;
        }

        try
        {
            var resolved = Catalog.Resolve(workspace.Name);
            var sample = new PartValues();
            foreach (var field in resolved.Fields)
            {
                sample[field.Key] = SampleValue(field);
            }

            var name = FilenameBuilder.Render(FilenameTemplate, FilenameBuilder.BuildTokens(resolved, "John Smith", sample));
            FilenamePreview = $"Preview: {name}.pdf";
        }
        catch (FormatException error)
        {
            FilenamePreview = $"Preview unavailable: {error.Message}";
        }
    }

    private static string SampleValue(FieldDefinition field) => field.Type switch
    {
        FieldType.Checkbox or FieldType.Toggle => "true",
        FieldType.Date => DateFieldFormat.Format(DateOnly.FromDateTime(DateTime.Today), field.DateFormat),
        FieldType.Currency => "134.06",
        FieldType.Number => "1234",
        FieldType.Choice => field.Options.FirstOrDefault(o => !o.Equals("Other", StringComparison.OrdinalIgnoreCase)) ?? "Option",
        _ when field.Default.Length > 0 => field.Default,
        _ when field.Placeholder.Length > 0 => field.Placeholder.Replace("e.g. ", "").Split(',')[0].Trim(),
        _ => field.Label
    };

    private static FieldRow Row(FieldDefinition field) =>
        new(field.Key, field.Label, TypeLabels.GetValueOrDefault(field.Type, "Text"), field.System);

    /// <summary>Saves shortly after the last change; open editors then rebuild with the new definition.</summary>
    private void ScheduleSave(string message)
    {
        _log.Info("Workspaces", message);
        SaveStatus = "Saving…";
        _pendingSave?.Cancel();
        var cts = _pendingSave = new CancellationTokenSource();
        _ = SaveSoonAsync(cts);
    }

    private async Task SaveSoonAsync(CancellationTokenSource cts)
    {
        try
        {
            await Task.Delay(600, cts.Token);
            _pendingSave = null;
            _ownSave = true;
            try
            {
                await _store.SaveAsync();
            }
            finally
            {
                _ownSave = false;
            }

            SaveStatus = "All changes saved";
        }
        catch (OperationCanceledException)
        {
        }
        catch (Exception error)
        {
            _crashLog.Write("Saving workspaces failed", error);
            SaveStatus = "Changes could not be saved. Details were saved to the log.";
        }
    }
}

/// <summary>Edits one library field (1.x custom field editor). Changes apply immediately.</summary>
public sealed partial class FieldEditorViewModel : ObservableObject
{
    private readonly FieldDefinition _field;
    private readonly Action _changed;
    private readonly bool _loading;

    public FieldEditorViewModel(FieldDefinition field, WorkspaceCatalog catalog, Action changed)
    {
        _field = field;
        _changed = changed;
        _loading = true;
        Label = field.Label;
        TypeLabel = WorkspacesViewModel.TypeLabels[field.Type];
        Placeholder = field.Placeholder;
        Default = field.Default;
        Required = field.Required;
        Autofill = field.Autofill;
        TitleCase = field.TitleCase;
        DateFormat = field.DateFormat;
        AutoToday = field.AutoToday;
        OptionsText = string.Join(Environment.NewLine, field.Options);
        Color = field.Color;
        Tooltip = field.Tooltip ?? "";
        InHeader = field.Placement == "header";
        ConditionFields = catalog.Fields.Values.Where(f => f.Key != field.Key).Select(f => f.Label).ToList();
        _conditionKeys = catalog.Fields.Values.Where(f => f.Key != field.Key).ToDictionary(f => f.Label, f => f.Key);
        HasCondition = field.Condition is not null;
        ConditionField = field.Condition is { } c ? catalog.Fields.GetValueOrDefault(c.Field)?.Label : ConditionFields.FirstOrDefault();
        ConditionEquals = field.Condition?.EqualsValue ?? "";
        _loading = false;
    }

    private readonly Dictionary<string, string> _conditionKeys;

    public string Key => _field.Key;
    public bool IsBuiltIn => _field.System;
    public IReadOnlyList<string> TypeLabels { get; } = WorkspacesViewModel.TypeLabels.Values.ToList();
    public IReadOnlyList<string> DateFormats { get; } = FieldDefinition.DateFormats;
    public IReadOnlyList<string> ConditionFields { get; }

    [ObservableProperty] public partial string Label { get; set; }
    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(IsDate), nameof(IsChoice), nameof(IsBoolean))]
    public partial string TypeLabel { get; set; }
    [ObservableProperty] public partial string Placeholder { get; set; }
    [ObservableProperty] public partial string Default { get; set; }
    [ObservableProperty] public partial bool Required { get; set; }
    [ObservableProperty] public partial bool Autofill { get; set; }
    [ObservableProperty] public partial bool TitleCase { get; set; }
    [ObservableProperty] public partial string DateFormat { get; set; }
    [ObservableProperty] public partial bool AutoToday { get; set; }
    [ObservableProperty] public partial string OptionsText { get; set; }
    [ObservableProperty] public partial string Color { get; set; }
    [ObservableProperty] public partial string? ColorError { get; private set; }
    [ObservableProperty] public partial string Tooltip { get; set; }
    [ObservableProperty] public partial bool InHeader { get; set; }
    [ObservableProperty] public partial bool HasCondition { get; set; }
    [ObservableProperty] public partial string? ConditionField { get; set; }
    [ObservableProperty] public partial string ConditionEquals { get; set; }

    private FieldType Type => WorkspacesViewModel.TypeLabels.First(p => p.Value == TypeLabel).Key;
    public bool IsDate => Type == FieldType.Date;
    public bool IsChoice => Type == FieldType.Choice;
    public bool IsBoolean => Type is FieldType.Checkbox or FieldType.Toggle;

    protected override void OnPropertyChanged(System.ComponentModel.PropertyChangedEventArgs e)
    {
        base.OnPropertyChanged(e);
        if (_loading || e.PropertyName is nameof(ColorError) or nameof(IsDate) or nameof(IsChoice) or nameof(IsBoolean))
        {
            return;
        }

        Apply();
    }

    private void Apply()
    {
        _field.Label = Label.Trim().Length > 0 ? Label.Trim() : _field.Key;
        _field.Type = Type;
        _field.Placeholder = Placeholder;
        _field.Default = IsBoolean ? (FieldDefinition.IsTrue(Default) ? "true" : "false") : Default;
        _field.Required = Required;
        _field.Autofill = Autofill;
        _field.TitleCase = TitleCase;
        _field.DateFormat = FieldDefinition.DateFormats.Contains(DateFormat) ? DateFormat : FieldDefinition.DefaultDateFormat;
        _field.AutoToday = IsDate && AutoToday;
        _field.Options = OptionsText.Split('\n').Select(o => o.Trim()).Where(o => o.Length > 0).ToList();
        _field.Tooltip = Tooltip.Trim().Length > 0 ? Tooltip.Trim() : null;
        _field.Placement = IsBoolean && InHeader ? "header" : null;
        _field.Condition = HasCondition && ConditionField is not null && _conditionKeys.TryGetValue(ConditionField, out var key)
            ? new FieldCondition { Field = key, EqualsValue = ConditionEquals.Trim() }
            : null;

        var color = Color.Trim();
        if (color.Length == 0 || System.Text.RegularExpressions.Regex.IsMatch(color, "^#?[0-9A-Fa-f]{6}$"))
        {
            _field.Color = color.Length == 0 ? "" : "#" + color.TrimStart('#').ToUpperInvariant();
            ColorError = null;
        }
        else
        {
            ColorError = "Use a hex color such as #3B8ED0 (or leave blank).";
        }

        _changed();
    }
}
