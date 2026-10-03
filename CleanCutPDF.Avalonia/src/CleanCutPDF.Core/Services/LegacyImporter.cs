using System.Text.Json;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Models;
using CleanCutPDF.Core.Pdf;
using CleanCutPDF.Core.Sessions;
using CleanCutPDF.Core.Workspaces;

namespace CleanCutPDF.Core.Services;

/// <summary>What was read from CleanCutPDF 1.x. Nothing is applied until the user confirms.</summary>
public sealed class LegacyImport
{
    public WorkspaceCatalog? Catalog { get; set; }
    public Action<AppSettings>? ApplySettings { get; set; }
    public List<FolderShortcut> FolderShortcuts { get; } = [];

    /// <summary>Keyboard shortcuts from keybinds.json (action id → gesture), not yet validated.</summary>
    public Dictionary<string, string> Keybinds { get; } = [];

    public SessionState Session { get; } = new();
    public List<string> HistoryLines { get; } = [];
    public List<string> Warnings { get; } = [];

    public string Summary =>
        $"{Catalog?.Workspaces.Count ?? 0} workspace(s), {Catalog?.Fields.Count(f => !f.Value.System) ?? 0} custom field(s), " +
        $"{Session.Documents.Count} open PDF(s), {Session.Folders.Count(f => f.Id != SessionFolder.InboxId)} Inbox folder(s), " +
        $"{FolderShortcuts.Count} folder shortcut(s), {HistoryLines.Count} export-history line(s)";
}

/// <summary>
/// Reads the 1.x data folder (~/.cleancutpdf) into the 2.x formats. It only
/// ever opens those files for reading. Applies the same migrations 1.x did on
/// load (v1.8 workspace_settings, pre-workspace settings, global auto-today).
/// </summary>
public sealed class LegacyImporter(AppPaths paths)
{
    public Task<LegacyImport> ReadAsync(CancellationToken cancellationToken = default) =>
        Task.Run(() => Read(cancellationToken), cancellationToken);

    private LegacyImport Read(CancellationToken cancellationToken)
    {
        var result = new LegacyImport();
        var directory = paths.LegacyDataDirectory;
        if (!Directory.Exists(directory))
        {
            result.Warnings.Add("No CleanCutPDF 1.x data folder was found.");
            return result;
        }

        // 1.x kept keyboard shortcuts in their own file: { "Open PDF": "ctrl+o", … }.
        if (TryParse(Path.Combine(directory, "keybinds.json"), result) is { } keybinds)
        {
            using (keybinds)
            {
                if (keybinds.RootElement.ValueKind == JsonValueKind.Object)
                {
                    foreach (var property in keybinds.RootElement.EnumerateObject().Where(p => p.Value.ValueKind == JsonValueKind.String))
                    {
                        if (Shortcuts.ShortcutCatalog.IdForLegacyName(property.Name) is { } id)
                        {
                            result.Keybinds[id] = property.Value.GetString() ?? "";
                        }
                    }
                }
            }
        }

        var settingsFile = Path.Combine(directory, "settings.json");
        if (TryParse(settingsFile, result) is { RootElement.ValueKind: JsonValueKind.Object } settings)
        {
            using (settings)
            {
                ReadSettings(settings.RootElement, result);
            }
        }

        cancellationToken.ThrowIfCancellationRequested();
        if (TryParse(Path.Combine(directory, "document_project.json"), result) is { } project)
        {
            using (project)
            {
                if (project.RootElement.TryGetProperty("folders", out var folders) && folders.ValueKind == JsonValueKind.Array)
                {
                    foreach (var folder in folders.EnumerateArray())
                    {
                        var id = Str(folder, "id");
                        var name = Str(folder, "name");
                        if (id.Length > 0 && name.Length > 0)
                        {
                            result.Session.Folders.Add(new SessionFolder { Id = id, Name = name });
                        }
                    }
                }
            }
        }

        if (TryParse(Path.Combine(directory, "sessions.json"), result) is { RootElement.ValueKind: JsonValueKind.Array } sessions)
        {
            using (sessions)
            {
                foreach (var item in sessions.RootElement.EnumerateArray())
                {
                    ReadSessionDocument(item, result);
                }
            }
        }

        result.Session.Normalize();

        var log = Path.Combine(directory, "full.log");
        if (File.Exists(log))
        {
            result.HistoryLines.AddRange(File.ReadLines(log).Where(line => line.Contains("Client:", StringComparison.Ordinal)));
        }

        return result;
    }

    private static void ReadSettings(JsonElement root, LegacyImport result)
    {
        var catalog = WorkspaceCatalog.CreateDefault();
        var hasWorkspaceSettings = root.TryGetProperty("workspace_settings", out var workspaceSettings)
                                   && workspaceSettings.ValueKind == JsonValueKind.Object;

        // Field library: built-ins stay, saved values win, user fields are added.
        if (root.TryGetProperty("custom_fields", out var fields) && fields.ValueKind == JsonValueKind.Object)
        {
            foreach (var property in fields.EnumerateObject().Where(p => p.Value.ValueKind == JsonValueKind.Object))
            {
                var field = catalog.Fields.TryGetValue(property.Name, out var existing) ? existing : new FieldDefinition();
                ApplyField(field, property.Name, property.Value);
                catalog.Fields[property.Name] = field;
            }
        }

        if (Bool(root, "autofill_todays_date") == true)
        {
            foreach (var field in catalog.Fields.Values.Where(f => f.Type == FieldType.Date))
            {
                field.AutoToday = true;
            }
        }

        if (root.TryGetProperty("workspaces", out var workspaces) && workspaces.ValueKind == JsonValueKind.Object
            && workspaces.EnumerateObject().Any())
        {
            catalog.Workspaces.Clear();
            foreach (var property in workspaces.EnumerateObject().Where(p => p.Value.ValueKind == JsonValueKind.Object))
            {
                catalog.Workspaces.Add(ReadWorkspace(property.Name, property.Value));
            }
        }

        // v1.8: filename template and Description default lived in workspace_settings.
        if (hasWorkspaceSettings)
        {
            foreach (var property in workspaceSettings.EnumerateObject().Where(p => p.Value.ValueKind == JsonValueKind.Object))
            {
                var workspace = catalog.Workspaces.FirstOrDefault(w => w.Name == property.Name);
                if (workspace is null)
                {
                    continue;
                }

                var template = Str(property.Value, "filename_template");
                if (template.Length > 0)
                {
                    workspace.FilenameTemplate = template;
                }

                var description = workspace.FieldOverrides.TryGetValue("description", out var o) ? o : new FieldOverride();
                if (property.Value.TryGetProperty("default_description", out var d) && d.ValueKind == JsonValueKind.String)
                {
                    description.Default = d.GetString();
                }

                description.Autofill = Bool(property.Value, "autofill_description") ?? description.Autofill;
                workspace.FieldOverrides["description"] = description;
            }
        }
        else if (catalog.Workspaces.FirstOrDefault(w => w.Name == WorkspaceCatalog.AccountingName) is { } accounting)
        {
            // Settings from before workspaces existed.
            var template = Str(root, "filename_template");
            if (template.Length > 0)
            {
                accounting.FilenameTemplate = template;
            }
        }

        catalog.Normalize();
        result.Catalog = catalog;

        if (root.TryGetProperty("folder_shortcuts", out var shortcuts) && shortcuts.ValueKind == JsonValueKind.Array)
        {
            foreach (var item in shortcuts.EnumerateArray())
            {
                var path = Str(item, "path");
                if (path.Length == 0)
                {
                    continue;
                }

                result.FolderShortcuts.Add(new FolderShortcut
                {
                    Path = path,
                    Label = Str(item, "label") is { Length: > 0 } label ? label : Path.GetFileName(path),
                    Icon = Str(item, "icon") is { Length: > 0 } icon ? icon : "📁",
                    Color = Str(item, "color")
                });
            }
        }

        var theme = Str(root, "theme");
        var exportFolder = Str(root, "export_folder");
        var defaultWorkspace = Str(root, "default_workspace");
        var quickSplitOrder = Str(root, "quick_split_filename_order");
        var removeBlank = Bool(root, "remove_blank_pages");
        var autoRestore = Bool(root, "auto_restore_session");
        var checkUpdates = Bool(root, "check_updates_on_startup");
        var suppressFuture = Bool(root, "suppressFutureDateWarning");
        var suppressNoSplit = Bool(root, "suppressNoSplitWarning");
        var shortcutsCopy = result.FolderShortcuts.ToList();
        var fontFamily = Str(root, "font_family");
        int? fontSize = root.TryGetProperty("font_size", out var sizeValue) && sizeValue.TryGetInt32(out var parsedSize)
            ? parsedSize
            : null;
        var keybinds = result.Keybinds;

        result.ApplySettings = settings =>
        {
            if (theme.Length > 0)
            {
                // 1.x themes were "Light Blue", "Dark Green", "Light Pink", …
                settings.Theme = theme.StartsWith("Dark", StringComparison.OrdinalIgnoreCase) ? AppThemeMode.Dark : AppThemeMode.Light;
                settings.Accent = theme.EndsWith("Green", StringComparison.OrdinalIgnoreCase) ? AppAccent.Green
                    : theme.EndsWith("Pink", StringComparison.OrdinalIgnoreCase) ? AppAccent.Pink
                    : AppAccent.Blue;
            }

            if (fontFamily.Length > 0)
            {
                // Segoe UI was the 1.x default; here the default is the built-in font.
                settings.FontFamily = fontFamily.Equals("Segoe UI", StringComparison.OrdinalIgnoreCase) ? "" : fontFamily;
            }

            if (fontSize is { } size)
            {
                // The 1.x default (12) corresponds to the default here.
                settings.FontSize = AppSettings.ClampFontSize(size - 12 + AppSettings.DefaultFontSize);
            }

            if (keybinds.Count > 0)
            {
                settings.Keybinds = Shortcuts.ShortcutCatalog.Clean(keybinds);
            }

            if (exportFolder.Length > 0)
            {
                settings.ExportFolder = exportFolder;
            }

            if (catalog.Workspaces.Any(w => w.Name == defaultWorkspace))
            {
                settings.DefaultWorkspace = defaultWorkspace;
            }

            if (Export.QuickSplitOrders.All.Contains(quickSplitOrder))
            {
                settings.QuickSplitFilenameOrder = quickSplitOrder;
            }

            settings.RemoveBlankPages = removeBlank ?? settings.RemoveBlankPages;
            settings.AutoRestoreSession = autoRestore ?? settings.AutoRestoreSession;
            settings.CheckUpdatesOnStartup = checkUpdates ?? settings.CheckUpdatesOnStartup;
            settings.WarnOnFutureDates = suppressFuture is { } f ? !f : settings.WarnOnFutureDates;
            settings.WarnWhenNoSplitMarkers = suppressNoSplit is { } n ? !n : settings.WarnWhenNoSplitMarkers;
            foreach (var shortcut in shortcutsCopy.Where(s => settings.FolderShortcuts.All(x => !PathsEqual(x.Path, s.Path))))
            {
                settings.FolderShortcuts.Add(shortcut);
            }
        };
    }

    private static void ApplyField(FieldDefinition field, string key, JsonElement json)
    {
        field.Key = key;
        field.Label = Str(json, "label") is { Length: > 0 } label ? label : field.Label.Length > 0 ? field.Label : key;
        if (Enum.TryParse<FieldType>(Str(json, "type").Replace("bool", "checkbox"), ignoreCase: true, out var type))
        {
            field.Type = type;
        }

        field.Placeholder = Str(json, "placeholder", field.Placeholder);
        if (json.TryGetProperty("default", out var defaultValue))
        {
            field.Default = ValueText(defaultValue);
        }

        field.Required = Bool(json, "required") ?? field.Required;
        field.Autofill = Bool(json, "autofill") ?? field.Autofill;
        field.TitleCase = Bool(json, "title_case") ?? field.TitleCase;
        field.AutoToday = Bool(json, "auto_today") ?? field.AutoToday;
        field.DateFormat = Str(json, "date_format", field.DateFormat);
        field.Color = Str(json, "color", field.Color);
        field.Tooltip = Str(json, "tooltip") is { Length: > 0 } tip ? tip : field.Tooltip;
        field.Placement = Str(json, "placement") is "header" ? "header" : field.Placement == "header" ? "header" : null;
        field.System = Bool(json, "system") ?? field.System;
        if (json.TryGetProperty("options", out var options) && options.ValueKind == JsonValueKind.Array)
        {
            field.Options = options.EnumerateArray().Select(ValueText).Where(o => o.Trim().Length > 0).ToList();
        }

        field.Condition = json.TryGetProperty("condition", out var condition) && condition.ValueKind == JsonValueKind.Object
                          && Str(condition, "field").Length > 0
            ? new FieldCondition { Field = Str(condition, "field"), EqualsValue = Str(condition, "equals") }
            : null;
    }

    private static WorkspaceDefinition ReadWorkspace(string name, JsonElement json)
    {
        var workspace = new WorkspaceDefinition
        {
            Name = name,
            ClientLabel = Str(json, "client_label", "Client Name"),
            Summary = Str(json, "summary", "Custom document workflow."),
            FilenameTemplate = Str(json, "filename_template", "{client}_{date}"),
            Permanent = Bool(json, "permanent") ?? name == WorkspaceCatalog.AccountingName
        };

        if (json.TryGetProperty("field_keys", out var keys) && keys.ValueKind == JsonValueKind.Array)
        {
            workspace.FieldKeys = keys.EnumerateArray().Select(ValueText).Where(k => k.Length > 0).ToList();
        }

        if (json.TryGetProperty("field_overrides", out var overrides) && overrides.ValueKind == JsonValueKind.Object)
        {
            foreach (var property in overrides.EnumerateObject().Where(p => p.Value.ValueKind == JsonValueKind.Object))
            {
                var o = new FieldOverride
                {
                    Autofill = Bool(property.Value, "autofill"),
                    Required = Bool(property.Value, "required"),
                    Label = Str(property.Value, "label") is { Length: > 0 } label ? label : null
                };
                if (property.Value.TryGetProperty("default", out var d))
                {
                    o.Default = ValueText(d);
                }

                workspace.FieldOverrides[property.Name] = o;
            }
        }

        if (json.TryGetProperty("notes", out var notes) && notes.ValueKind == JsonValueKind.Array)
        {
            foreach (var note in notes.EnumerateArray())
            {
                var text = Str(note, "text").Trim();
                if (text.Length > 0)
                {
                    workspace.Notes.Add(new WorkspaceNote
                    {
                        Id = Str(note, "id") is { Length: > 0 } id ? id : Guid.NewGuid().ToString("N")[..8],
                        Text = text,
                        BeforeField = Str(note, "before_field", WorkspaceNote.EndOfForm)
                    });
                }
            }
        }

        return workspace;
    }

    private static void ReadSessionDocument(JsonElement item, LegacyImport result)
    {
        var path = Str(item, "file_path");
        if (path.Length == 0)
        {
            return;
        }

        if (!File.Exists(path))
        {
            result.Warnings.Add($"Skipped a saved PDF that no longer exists: {Path.GetFileName(path)}");
            return;
        }

        var document = new SessionDocument
        {
            FilePath = path,
            ClientName = Str(item, "client_name"),
            Workspace = Str(item, "workspace", WorkspaceCatalog.AccountingName),
            FolderId = Str(item, "folder_id", SessionFolder.InboxId)
        };

        // 1.x stored the modification time in nanoseconds since 1970 (UTC).
        if (item.TryGetProperty("file_signature", out var signature) && signature.ValueKind == JsonValueKind.Object
            && signature.TryGetProperty("size", out var size) && size.TryGetInt64(out var bytes)
            && signature.TryGetProperty("mtime_ns", out var mtime) && mtime.TryGetInt64(out var nanoseconds)
            && item.TryGetProperty("detected_ranges", out var ranges) && ranges.ValueKind == JsonValueKind.Array)
        {
            document.FileSignature = new FileSignature(bytes, DateTime.UnixEpoch.Ticks + nanoseconds / 100);
            document.DetectedRanges = ranges.EnumerateArray()
                .Select(r => new PageRange(r.GetProperty("start").GetInt32(), r.GetProperty("end").GetInt32()))
                .ToList();
            document.PageCount = 0; // Read from the file on restore; the cached ranges are still reused.
        }

        var data = item.TryGetProperty("workspace_data", out var workspaceData) && workspaceData.ValueKind == JsonValueKind.Object
            ? workspaceData
            : default;
        if (data.ValueKind == JsonValueKind.Object)
        {
            foreach (var workspace in data.EnumerateObject().Where(p => p.Value.ValueKind == JsonValueKind.Array))
            {
                document.WorkspaceData[workspace.Name] = workspace.Value.EnumerateArray().Select(Row).ToList();
            }
        }
        else if (item.TryGetProperty("parts", out var parts) && parts.ValueKind == JsonValueKind.Array)
        {
            document.WorkspaceData[WorkspaceCatalog.AccountingName] = parts.EnumerateArray().Select(Row).ToList();
        }

        result.Session.Documents.Add(document);

        static Dictionary<string, string> Row(JsonElement row) =>
            row.ValueKind != JsonValueKind.Object
                ? new Dictionary<string, string>()
                : row.EnumerateObject().Where(p => p.Name != "range").ToDictionary(p => p.Name, p => ValueText(p.Value));
    }

    private static JsonDocument? TryParse(string path, LegacyImport result)
    {
        if (!File.Exists(path))
        {
            return null;
        }

        try
        {
            using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
            return JsonDocument.Parse(stream);
        }
        catch (Exception error) when (error is JsonException or IOException or UnauthorizedAccessException)
        {
            result.Warnings.Add($"{Path.GetFileName(path)} could not be read: {error.Message}");
            return null;
        }
    }

    private static string Str(JsonElement json, string name, string fallback = "") =>
        json.ValueKind == JsonValueKind.Object && json.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.String
            ? value.GetString() ?? fallback
            : fallback;

    private static bool? Bool(JsonElement json, string name) =>
        json.ValueKind == JsonValueKind.Object && json.TryGetProperty(name, out var value)
            ? value.ValueKind switch { JsonValueKind.True => true, JsonValueKind.False => false, _ => null }
            : null;

    /// <summary>Python values as the 2.x string form: booleans become "true"/"false".</summary>
    private static string ValueText(JsonElement value) => value.ValueKind switch
    {
        JsonValueKind.True => "true",
        JsonValueKind.False => "false",
        JsonValueKind.String => value.GetString() ?? "",
        JsonValueKind.Number => value.GetRawText(),
        _ => ""
    };

    private static bool PathsEqual(string a, string b) =>
        string.Equals(Path.GetFullPath(a).TrimEnd('\\', '/'), Path.GetFullPath(b).TrimEnd('\\', '/'), StringComparison.OrdinalIgnoreCase);
}
