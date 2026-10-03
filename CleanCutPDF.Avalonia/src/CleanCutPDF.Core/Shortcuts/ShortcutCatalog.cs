namespace CleanCutPDF.Core.Shortcuts;

/// <summary>One action that can have a keyboard shortcut.</summary>
/// <param name="Id">Stable id stored in settings.</param>
/// <param name="Label">Name shown to the user (and the 1.x keybinds.json name).</param>
/// <param name="DefaultGesture">1.x default, or empty when the action starts unassigned.</param>
public sealed record ShortcutAction(string Id, string Label, string DefaultGesture);

/// <summary>
/// The rebindable keyboard shortcuts. Gestures are stored the way 1.x stored
/// them: lower-case, joined with "+", modifiers first ("ctrl+shift+z").
/// </summary>
public static class ShortcutCatalog
{
    public const string OpenPdf = "open_pdf";
    public const string ClosePdf = "close_pdf";
    public const string Export = "export";
    public const string ResetForm = "reset_form";
    public const string Quit = "quit";
    public const string SearchLogs = "search_logs";
    public const string UndoLastExport = "undo_last_export";
    public const string PasteClipboard = "paste_clipboard";
    public const string ClearLog = "clear_log";
    public const string FocusClientName = "focus_client_name";
    public const string FocusFirstPart = "focus_first_part";
    public const string SelectExportFolder = "select_export_folder";

    /// <summary>The debug console shortcut is fixed and cannot be rebound or reused.</summary>
    public const string DebugConsoleGesture = "ctrl+alt+d";

    public static readonly IReadOnlyList<ShortcutAction> Actions =
    [
        new(OpenPdf, "Open PDF", "ctrl+o"),
        new(ClosePdf, "Close PDF", "ctrl+w"),
        new(Export, "Export PDFs", "ctrl+e"),
        new(ResetForm, "Reset Form", "ctrl+r"),
        new(Quit, "Quit", "ctrl+q"),
        new(SearchLogs, "Search Logs", "ctrl+f"),
        new(UndoLastExport, "Undo Last Export", "ctrl+shift+z"),
        new(PasteClipboard, "Paste Clipboard", "ctrl+shift+v"),
        new(ClearLog, "Clear Log", ""),
        new(FocusClientName, "Focus Client Name", ""),
        new(FocusFirstPart, "Focus First Part", ""),
        new(SelectExportFolder, "Select Export Folder", "")
    ];

    private static readonly string[] ModifierOrder = ["ctrl", "alt", "shift", "cmd"];

    private static readonly Dictionary<string, string> Aliases = new(StringComparer.OrdinalIgnoreCase)
    {
        ["control"] = "ctrl", ["option"] = "alt", ["meta"] = "cmd", ["command"] = "cmd", ["win"] = "cmd",
        ["return"] = "enter", ["escape"] = "esc", ["del"] = "delete"
    };

    /// <summary>Combinations text boxes need for editing, which a shortcut must not take over.</summary>
    private static readonly HashSet<string> EditingGestures =
        ["ctrl+a", "ctrl+c", "ctrl+v", "ctrl+x", "ctrl+y", "ctrl+z"];

    /// <summary>1.x action names that differ from the 2.x labels.</summary>
    private static readonly Dictionary<string, string> LegacyNames = new(StringComparer.OrdinalIgnoreCase)
    {
        ["Close Tab"] = ClosePdf,
        ["Reset"] = ResetForm
    };

    public static ShortcutAction? Find(string id) => Actions.FirstOrDefault(a => a.Id == id);

    /// <summary>The action id for a 1.x keybinds.json name, or null when 2.x has no such action.</summary>
    public static string? IdForLegacyName(string name) =>
        LegacyNames.TryGetValue(name.Trim(), out var id)
            ? id
            : Actions.FirstOrDefault(a => string.Equals(a.Label, name.Trim(), StringComparison.OrdinalIgnoreCase))?.Id;

    /// <summary>
    /// Canonical form of a gesture: lower-case, known aliases replaced,
    /// modifiers in a fixed order. Returns "" when there is no key.
    /// </summary>
    public static string Normalize(string? gesture)
    {
        if (string.IsNullOrWhiteSpace(gesture))
        {
            return "";
        }

        var parts = gesture.Split('+', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .Select(p => Aliases.TryGetValue(p, out var alias) ? alias : p.ToLowerInvariant())
            .ToList();
        var keys = parts.Where(p => !ModifierOrder.Contains(p)).ToList();
        if (keys.Count != 1)
        {
            return "";
        }

        return string.Join("+", ModifierOrder.Where(parts.Contains).Append(keys[0]));
    }

    /// <summary>"ctrl+shift+z" → "Ctrl+Shift+Z" (empty → "Not set").</summary>
    public static string Display(string gesture) =>
        gesture.Length == 0
            ? "Not set"
            : string.Join("+", gesture.Split('+').Select(p => p.Length <= 1 ? p.ToUpperInvariant() : char.ToUpperInvariant(p[0]) + p[1..]));

    /// <summary>Every action's current gesture: the user's change if there is one, otherwise the default.</summary>
    public static IReadOnlyDictionary<string, string> Effective(IReadOnlyDictionary<string, string> overrides) =>
        Actions.ToDictionary(a => a.Id, a => overrides.TryGetValue(a.Id, out var custom) ? Normalize(custom) : a.DefaultGesture);

    /// <summary>The action a gesture runs, or null.</summary>
    public static string? Match(IReadOnlyDictionary<string, string> overrides, string gesture)
    {
        var normalized = Normalize(gesture);
        return normalized.Length == 0
            ? null
            : Effective(overrides).FirstOrDefault(pair => pair.Value == normalized).Key;
    }

    /// <summary>
    /// Why a gesture cannot be assigned to an action, or null when it can.
    /// </summary>
    public static string? Validate(IReadOnlyDictionary<string, string> overrides, string actionId, string gesture)
    {
        var normalized = Normalize(gesture);
        if (ValidateShape(normalized) is { } problem)
        {
            return problem;
        }

        var taken = Effective(overrides).FirstOrDefault(pair => pair.Value == normalized && pair.Key != actionId).Key;
        return taken is null ? null : $"{Display(normalized)} is already used by {Find(taken)!.Label}.";
    }

    /// <summary>Checks a normalized gesture on its own (not against other actions).</summary>
    private static string? ValidateShape(string normalized)
    {
        if (normalized.Length == 0)
        {
            return "That is not a key combination.";
        }

        var parts = normalized.Split('+');
        var key = parts[^1];
        var isFunctionKey = key.Length >= 2 && key[0] == 'f' && int.TryParse(key[1..], out var n) && n is >= 1 and <= 24;
        if (!isFunctionKey && !parts.Contains("ctrl") && !parts.Contains("alt") && !parts.Contains("cmd"))
        {
            return "Shortcuts need Ctrl or Alt (or a function key), so typing is not affected.";
        }

        if (normalized == DebugConsoleGesture)
        {
            return $"{Display(normalized)} is reserved for the debug console.";
        }

        if (EditingGestures.Contains(normalized))
        {
            return $"{Display(normalized)} is used for editing text (copy, paste, undo, select all).";
        }

        return null;
    }

    /// <summary>
    /// The overrides after assigning a gesture ("" = no shortcut). A value
    /// equal to the default is not stored.
    /// </summary>
    public static Dictionary<string, string> Assign(IReadOnlyDictionary<string, string> overrides, string actionId, string gesture)
    {
        var result = Clean(overrides);
        var normalized = Normalize(gesture);
        if (Find(actionId) is not { } action)
        {
            return result;
        }

        if (normalized == action.DefaultGesture)
        {
            result.Remove(actionId);
        }
        else
        {
            result[actionId] = normalized;
        }

        return result;
    }

    /// <summary>
    /// Drops unknown actions and anything unusable or duplicated, so a
    /// hand-edited or imported file can never leave two actions on one gesture.
    /// </summary>
    public static Dictionary<string, string> Clean(IReadOnlyDictionary<string, string> overrides)
    {
        var result = new Dictionary<string, string>();
        foreach (var action in Actions)
        {
            if (!overrides.TryGetValue(action.Id, out var raw))
            {
                continue;
            }

            var normalized = Normalize(raw);
            if (normalized == action.DefaultGesture)
            {
                continue;
            }

            if (normalized.Length == 0)
            {
                // Explicitly unassigned (only meaningful when there is a default to turn off).
                if (action.DefaultGesture.Length > 0 && string.IsNullOrWhiteSpace(raw))
                {
                    result[action.Id] = "";
                }

                continue;
            }

            if (ValidateShape(normalized) is null && !result.ContainsValue(normalized))
            {
                result[action.Id] = normalized;
            }
        }

        // A changed shortcut wins over another action's default that it now collides with.
        foreach (var action in Actions.Where(a => a.DefaultGesture.Length > 0 && !result.ContainsKey(a.Id)))
        {
            if (result.Any(pair => pair.Value == action.DefaultGesture))
            {
                result[action.Id] = "";
            }
        }

        return result;
    }
}
