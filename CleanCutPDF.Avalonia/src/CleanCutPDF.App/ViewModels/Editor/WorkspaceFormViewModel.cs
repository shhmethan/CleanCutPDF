using CleanCutPDF.Core.Export;
using CleanCutPDF.Core.Naming;
using CleanCutPDF.Core.Pdf;
using CleanCutPDF.Core.Workspaces;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace CleanCutPDF.App.ViewModels.Editor;

/// <summary>One Part (a page range) with its fields.</summary>
public sealed partial class PartViewModel : ObservableObject
{
    private readonly Action<int> _jumpToPage;

    public PartViewModel(int index, PageRange range, string noun, IReadOnlyList<FieldViewModel> fields,
        IReadOnlyList<string> topNotes, IReadOnlyList<string> endNotes, Action<int> jumpToPage)
    {
        Index = index;
        Range = range;
        Title = noun == "Part"
            ? $"Part {index + 1} — Pages {range.Start + 1} to {range.End + 1}"
            : $"{noun} — Pages {range.Start + 1} to {range.End + 1}";
        Fields = fields;

        // A custom layout places the body fields; header toggles stay in the header either way,
        // so a layout nobody changed looks exactly like the automatic form.
        HeaderFields = fields.Where(f => f.Definition.IsHeaderField).ToList();
        var body = fields.Where(f => !f.Definition.IsHeaderField).ToList();
        IsFreeform = body.Count > 0 && body.All(f => f.Tile is not null);
        BodyFields = IsFreeform ? [] : body;
        FreeformFields = IsFreeform ? body : [];
        TopNotes = topNotes;
        EndNotes = endNotes;
        _jumpToPage = jumpToPage;
    }

    public int Index { get; }
    public PageRange Range { get; }
    public string Title { get; }
    public IReadOnlyList<FieldViewModel> Fields { get; }
    public IReadOnlyList<FieldViewModel> HeaderFields { get; }
    public IReadOnlyList<FieldViewModel> BodyFields { get; }

    /// <summary>True when the workspace uses a Layout Designer layout.</summary>
    public bool IsFreeform { get; }

    public IReadOnlyList<FieldViewModel> FreeformFields { get; }
    public IReadOnlyList<string> TopNotes { get; }
    public IReadOnlyList<string> EndNotes { get; }

    public FieldViewModel? Field(string key) => Fields.FirstOrDefault(f => f.Key == key);

    public PartValues Values() => new(Fields.ToDictionary(f => f.Key, f => f.Value));

    /// <summary>Clicking a Part title shows its first page in the preview.</summary>
    [RelayCommand]
    private void ShowInPreview() => _jumpToPage(Range.Start);
}

/// <summary>
/// The workspace form for one document: one Part per page range, with
/// 1.x autofill (a value typed in a Part carries into later Parts that still
/// hold the previously carried value) and conditional field visibility.
/// </summary>
public sealed class WorkspaceFormViewModel
{
    private readonly DateOnly _today;
    private bool _suppressAutofill;

    public WorkspaceFormViewModel(ResolvedWorkspace workspace, IReadOnlyList<PageRange> ranges,
        IReadOnlyList<Dictionary<string, string>>? savedRows, Action<int> jumpToPage, DateOnly today,
        string partNoun = "Part")
    {
        Workspace = workspace;
        _today = today;
        var notesByPosition = workspace.Notes.ToLookup(n => n.BeforeField, n => n.Text.Trim());

        var parts = new List<PartViewModel>();
        for (var i = 0; i < ranges.Count; i++)
        {
            var saved = savedRows is not null && i < savedRows.Count ? savedRows[i] : null;
            var fields = new List<FieldViewModel>();
            foreach (var definition in workspace.Fields)
            {
                var field = FieldViewModel.Create(definition, notesByPosition[definition.Key].ToList(),
                    workspace.Layout?.Tiles.GetValueOrDefault(definition.Key));
                field.Value = saved is not null && saved.TryGetValue(definition.Key, out var value)
                    ? value
                    : FieldRules.InitialValue(definition, today);
                if (definition.Type == FieldType.Date && definition.AutoToday && string.IsNullOrWhiteSpace(field.Value))
                {
                    field.Value = FieldRules.InitialValue(definition, today);
                }

                fields.Add(field);
            }

            var part = new PartViewModel(i, ranges[i], partNoun, fields,
                notesByPosition[WorkspaceNote.TopOfForm].ToList(),
                notesByPosition[WorkspaceNote.EndOfForm].ToList(), jumpToPage);
            parts.Add(part);
        }

        Parts = parts;
        foreach (var part in Parts)
        {
            RefreshVisibility(part);
            foreach (var field in part.Fields)
            {
                field.ValueChanged += (changed, old, value) => OnFieldChanged(part, changed, old, value);
            }
        }
    }

    public ResolvedWorkspace Workspace { get; }
    public IReadOnlyList<PartViewModel> Parts { get; }

    /// <summary>Raised after any field value changes (used to schedule a session save).</summary>
    public event EventHandler? Changed;

    public List<Dictionary<string, string>> Capture() =>
        Parts.Select(p => p.Fields.ToDictionary(f => f.Key, f => f.Value)).ToList();

    public IReadOnlyList<PartInput> ToPartInputs() =>
        Parts.Select(p => new PartInput(p.Range, p.Values())).ToList();

    /// <summary>Reset Form: every field back to its default (Date fields set to auto-today get today again).</summary>
    public void Reset()
    {
        _suppressAutofill = true;
        try
        {
            foreach (var field in Parts.SelectMany(p => p.Fields))
            {
                field.Value = FieldRules.InitialValue(field.Definition, _today);
            }
        }
        finally
        {
            _suppressAutofill = false;
        }

        foreach (var part in Parts)
        {
            RefreshVisibility(part);
        }

        Changed?.Invoke(this, EventArgs.Empty);
    }

    private void OnFieldChanged(PartViewModel part, FieldViewModel field, string old, string value)
    {
        if (!_suppressAutofill && field.Definition.Autofill)
        {
            _suppressAutofill = true;
            try
            {
                for (var j = part.Index + 1; j < Parts.Count; j++)
                {
                    var target = Parts[j].Field(field.Key);
                    if (target is null)
                    {
                        continue;
                    }

                    // Only update a later Part while it still matches what was carried
                    // into it; once the user edits it by hand it is left alone. Text also
                    // follows along while the user is typing forward.
                    var current = target.Value;
                    var follows = current == old
                                  || (!field.Definition.IsBoolean && current == (value.Length > 0 ? value[..^1] : ""));
                    if (follows)
                    {
                        target.Value = value;
                        RefreshVisibility(Parts[j]);
                    }
                }
            }
            finally
            {
                _suppressAutofill = false;
            }
        }

        RefreshVisibility(part);
        Changed?.Invoke(this, EventArgs.Empty);
    }

    private void RefreshVisibility(PartViewModel part)
    {
        var values = part.Values();
        foreach (var field in part.Fields)
        {
            field.IsVisible = FieldRules.IsVisible(field.Definition, values, Workspace);
        }
    }
}
