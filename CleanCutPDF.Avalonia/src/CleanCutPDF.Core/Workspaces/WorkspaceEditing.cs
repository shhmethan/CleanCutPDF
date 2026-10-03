using System.Text.RegularExpressions;

namespace CleanCutPDF.Core.Workspaces;

/// <summary>Raised with a message that can be shown to the user as-is.</summary>
public sealed class WorkspaceEditException(string message) : Exception(message);

/// <summary>Editing operations on the catalog, with the same rules as the 1.x settings screens.</summary>
public static partial class WorkspaceEditing
{
    public static WorkspaceDefinition Find(this WorkspaceCatalog catalog, string name) =>
        catalog.Workspaces.FirstOrDefault(w => w.Name == name)
        ?? throw new WorkspaceEditException($"The workspace “{name}” no longer exists.");

    /// <summary>
    /// Merges an imported catalog (1.x): imported workspaces and fields replace
    /// ones with the same name/key; anything created only here is kept.
    /// </summary>
    public static void Merge(this WorkspaceCatalog catalog, WorkspaceCatalog imported)
    {
        foreach (var (key, field) in imported.Fields)
        {
            catalog.Fields[key] = field.Clone();
        }

        foreach (var workspace in imported.Workspaces)
        {
            var index = catalog.Workspaces.FindIndex(w => w.Name == workspace.Name);
            if (index >= 0)
            {
                catalog.Workspaces[index] = workspace;
            }
            else
            {
                catalog.Workspaces.Add(workspace);
            }
        }

        catalog.Normalize();
    }

    public static WorkspaceDefinition AddWorkspace(this WorkspaceCatalog catalog, string name)
    {
        name = ValidateName(catalog, name, except: null);
        var workspace = new WorkspaceDefinition
        {
            Name = name,
            ClientLabel = "Client Name",
            Summary = "Custom document workflow.",
            FilenameTemplate = "{client}_{date}"
        };
        catalog.Workspaces.Add(workspace);
        return workspace;
    }

    public static void RenameWorkspace(this WorkspaceCatalog catalog, string oldName, string newName)
    {
        var workspace = catalog.Find(oldName);
        if (workspace.Permanent || oldName == WorkspaceCatalog.AccountingName)
        {
            throw new WorkspaceEditException("Accounting cannot be renamed.");
        }

        workspace.Name = ValidateName(catalog, newName, except: oldName);
    }

    public static void DeleteWorkspace(this WorkspaceCatalog catalog, string name)
    {
        var workspace = catalog.Find(name);
        if (workspace.Permanent || name == WorkspaceCatalog.AccountingName)
        {
            throw new WorkspaceEditException("Accounting cannot be deleted.");
        }

        catalog.Workspaces.Remove(workspace);
    }

    /// <summary>Adds a field to the library. The key is derived from the label (e.g. "Invoice #" → invoice).</summary>
    public static FieldDefinition AddField(this WorkspaceCatalog catalog, string label)
    {
        label = (label ?? "").Trim();
        if (label.Length == 0)
        {
            throw new WorkspaceEditException("Enter a field name.");
        }

        var baseKey = NonKeyCharacters().Replace(label.ToLowerInvariant(), "_").Trim('_');
        if (baseKey.Length == 0)
        {
            baseKey = "field";
        }

        var key = baseKey;
        for (var counter = 2; catalog.Fields.ContainsKey(key); counter++)
        {
            key = $"{baseKey}_{counter}";
        }

        var field = new FieldDefinition { Key = key, Label = label, Autofill = true, Options = ["Other"] };
        catalog.Fields[key] = field;
        return field;
    }

    /// <summary>Deletes a custom field everywhere it is used. Built-in fields can only be unassigned.</summary>
    public static void DeleteField(this WorkspaceCatalog catalog, string key)
    {
        if (!catalog.Fields.TryGetValue(key, out var field))
        {
            return;
        }

        if (field.System)
        {
            throw new WorkspaceEditException("Built-in fields can be edited or unassigned, but not deleted.");
        }

        catalog.Fields.Remove(key);
        foreach (var workspace in catalog.Workspaces)
        {
            workspace.UnassignField(key);
        }

        foreach (var other in catalog.Fields.Values.Where(f => f.Condition?.Field == key))
        {
            other.Condition = null;
        }
    }

    public static void AssignField(this WorkspaceDefinition workspace, string key)
    {
        if (!workspace.FieldKeys.Contains(key))
        {
            workspace.FieldKeys.Add(key);
        }
    }

    /// <summary>Removes a field from a workspace; notes attached to it move to the end of the form.</summary>
    public static void UnassignField(this WorkspaceDefinition workspace, string key)
    {
        workspace.FieldKeys.Remove(key);
        workspace.FieldOverrides.Remove(key);
        foreach (var note in workspace.Notes.Where(n => n.BeforeField == key))
        {
            note.BeforeField = WorkspaceNote.EndOfForm;
        }
    }

    public static void MoveField(this WorkspaceDefinition workspace, string key, int direction)
    {
        var index = workspace.FieldKeys.IndexOf(key);
        var target = index + direction;
        if (index < 0 || target < 0 || target >= workspace.FieldKeys.Count)
        {
            return;
        }

        (workspace.FieldKeys[index], workspace.FieldKeys[target]) = (workspace.FieldKeys[target], workspace.FieldKeys[index]);
    }

    /// <summary>Tokens offered by the filename editor for a workspace (1.x get_filename_editor_fields).</summary>
    public static IReadOnlyList<(string Token, string Label)> FilenameTokens(this WorkspaceCatalog catalog, string workspaceName)
    {
        var workspace = catalog.Resolve(workspaceName);
        var tokens = new List<(string, string)> { ("client", workspace.ClientLabel) };
        tokens.AddRange(workspace.Fields.Select(f => (f.Key, f.Key == "date" ? "Date" : f.Label)));
        if (workspace.Fields.Any(f => f.Key == "agency") || workspace.Fields.Any(f => f.Key == "description"))
        {
            tokens.Add(("agency_description", "Agency + Description"));
        }

        tokens.Add(("workspace", "Workspace Name"));
        return tokens;
    }

    private static string ValidateName(WorkspaceCatalog catalog, string name, string? except)
    {
        name = (name ?? "").Trim();
        if (name.Length == 0)
        {
            throw new WorkspaceEditException("Enter a workspace name.");
        }

        if (catalog.Workspaces.Any(w => w.Name != except && string.Equals(w.Name, name, StringComparison.OrdinalIgnoreCase)))
        {
            throw new WorkspaceEditException($"A workspace named “{name}” already exists.");
        }

        return name;
    }

    [GeneratedRegex("[^a-z0-9]+")]
    private static partial Regex NonKeyCharacters();
}
