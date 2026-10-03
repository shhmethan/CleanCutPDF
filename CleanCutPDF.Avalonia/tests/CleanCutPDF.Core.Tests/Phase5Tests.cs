using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Models;
using CleanCutPDF.Core.Services;
using CleanCutPDF.Core.Shortcuts;
using CleanCutPDF.Core.Workspaces;

namespace CleanCutPDF.Core.Tests;

public sealed class Phase5Tests : IDisposable
{
    private static readonly IReadOnlyDictionary<string, string> NoChanges = new Dictionary<string, string>();

    private readonly TempDirectory _temp = new();
    private readonly AppPaths _paths;

    public Phase5Tests()
    {
        _paths = new AppPaths(Path.Combine(_temp.Path, "data"), Path.Combine(_temp.Path, "legacy"));
        _paths.EnsureCreated();
    }

    // ───── Keyboard shortcuts ─────

    [Fact]
    public void Default_shortcuts_match_1x()
    {
        var effective = ShortcutCatalog.Effective(NoChanges);
        Assert.Equal("ctrl+o", effective[ShortcutCatalog.OpenPdf]);
        Assert.Equal("ctrl+w", effective[ShortcutCatalog.ClosePdf]);
        Assert.Equal("ctrl+e", effective[ShortcutCatalog.Export]);
        Assert.Equal("ctrl+r", effective[ShortcutCatalog.ResetForm]);
        Assert.Equal("ctrl+q", effective[ShortcutCatalog.Quit]);
        Assert.Equal("ctrl+f", effective[ShortcutCatalog.SearchLogs]);
        Assert.Equal("ctrl+shift+z", effective[ShortcutCatalog.UndoLastExport]);
        Assert.Equal("ctrl+shift+v", effective[ShortcutCatalog.PasteClipboard]);
        Assert.Equal("", effective[ShortcutCatalog.ClearLog]);
        Assert.Equal(12, effective.Count);

        // No two defaults share a gesture.
        var assigned = effective.Values.Where(g => g.Length > 0).ToList();
        Assert.Equal(assigned.Count, assigned.Distinct().Count());
    }

    [Theory]
    [InlineData("Ctrl+Shift+Z", "ctrl+shift+z")]
    [InlineData("shift+ctrl+z", "ctrl+shift+z")]
    [InlineData(" Control + Alt + Return ", "ctrl+alt+enter")]
    [InlineData("alt+F4", "alt+f4")]
    [InlineData("ctrl+", "")]
    [InlineData("ctrl+a+b", "")]
    [InlineData("", "")]
    [InlineData(null, "")]
    public void Gestures_are_normalized(string? input, string expected) =>
        Assert.Equal(expected, ShortcutCatalog.Normalize(input));

    [Fact]
    public void Gestures_display_in_title_case()
    {
        Assert.Equal("Ctrl+Shift+Z", ShortcutCatalog.Display("ctrl+shift+z"));
        Assert.Equal("Alt+F4", ShortcutCatalog.Display("alt+f4"));
        Assert.Equal("Not set", ShortcutCatalog.Display(""));
    }

    [Fact]
    public void Key_presses_match_the_assigned_action()
    {
        Assert.Equal(ShortcutCatalog.OpenPdf, ShortcutCatalog.Match(NoChanges, "ctrl+o"));
        Assert.Equal(ShortcutCatalog.UndoLastExport, ShortcutCatalog.Match(NoChanges, "shift+ctrl+z"));
        Assert.Null(ShortcutCatalog.Match(NoChanges, "ctrl+k"));
        Assert.Null(ShortcutCatalog.Match(NoChanges, "")); // Unassigned actions never match.

        var changed = ShortcutCatalog.Assign(NoChanges, ShortcutCatalog.OpenPdf, "ctrl+k");
        Assert.Equal(ShortcutCatalog.OpenPdf, ShortcutCatalog.Match(changed, "ctrl+k"));
        Assert.Null(ShortcutCatalog.Match(changed, "ctrl+o"));
    }

    [Fact]
    public void Conflicts_and_unsafe_gestures_are_refused()
    {
        Assert.Contains("Close PDF", ShortcutCatalog.Validate(NoChanges, ShortcutCatalog.OpenPdf, "ctrl+w"));
        Assert.Contains("debug console", ShortcutCatalog.Validate(NoChanges, ShortcutCatalog.OpenPdf, "ctrl+alt+d"));
        Assert.Contains("editing text", ShortcutCatalog.Validate(NoChanges, ShortcutCatalog.OpenPdf, "ctrl+c"));
        Assert.Contains("Ctrl or Alt", ShortcutCatalog.Validate(NoChanges, ShortcutCatalog.OpenPdf, "o"));
        Assert.Contains("Ctrl or Alt", ShortcutCatalog.Validate(NoChanges, ShortcutCatalog.OpenPdf, "shift+o"));
        Assert.NotNull(ShortcutCatalog.Validate(NoChanges, ShortcutCatalog.OpenPdf, "ctrl+"));

        Assert.Null(ShortcutCatalog.Validate(NoChanges, ShortcutCatalog.OpenPdf, "ctrl+o")); // Its own gesture.
        Assert.Null(ShortcutCatalog.Validate(NoChanges, ShortcutCatalog.OpenPdf, "ctrl+k"));
        Assert.Null(ShortcutCatalog.Validate(NoChanges, ShortcutCatalog.OpenPdf, "f5"));
        Assert.Null(ShortcutCatalog.Validate(NoChanges, ShortcutCatalog.ClearLog, "ctrl+shift+delete"));

        // Once Close PDF moves, its old gesture is free.
        var moved = ShortcutCatalog.Assign(NoChanges, ShortcutCatalog.ClosePdf, "ctrl+k");
        Assert.Null(ShortcutCatalog.Validate(moved, ShortcutCatalog.OpenPdf, "ctrl+w"));
        Assert.Contains("Close PDF", ShortcutCatalog.Validate(moved, ShortcutCatalog.OpenPdf, "ctrl+k"));
    }

    [Fact]
    public void Only_changes_from_the_defaults_are_stored()
    {
        var changed = ShortcutCatalog.Assign(NoChanges, ShortcutCatalog.OpenPdf, "Ctrl+K");
        Assert.Equal("ctrl+k", Assert.Single(changed).Value);

        var removed = ShortcutCatalog.Assign(changed, ShortcutCatalog.Quit, "");
        Assert.Equal("", removed[ShortcutCatalog.Quit]);
        Assert.Equal("", ShortcutCatalog.Effective(removed)[ShortcutCatalog.Quit]);
        Assert.Null(ShortcutCatalog.Match(removed, "ctrl+q"));

        var restored = ShortcutCatalog.Assign(removed, ShortcutCatalog.OpenPdf, "ctrl+o");
        Assert.DoesNotContain(ShortcutCatalog.OpenPdf, restored.Keys);
    }

    [Fact]
    public void Hand_edited_shortcuts_are_cleaned()
    {
        var cleaned = ShortcutCatalog.Clean(new Dictionary<string, string>
        {
            ["no_such_action"] = "ctrl+k",
            [ShortcutCatalog.OpenPdf] = "ctrl+w", // Takes Close PDF's default…
            [ShortcutCatalog.Export] = "ctrl+alt+d", // Reserved.
            [ShortcutCatalog.ResetForm] = "x", // No modifier.
            [ShortcutCatalog.ClearLog] = "CTRL+L",
            [ShortcutCatalog.FocusClientName] = "ctrl+l", // Duplicate of the one above.
            [ShortcutCatalog.Quit] = "ctrl+q" // Same as the default.
        });

        Assert.Equal("ctrl+w", cleaned[ShortcutCatalog.OpenPdf]);
        Assert.Equal("", cleaned[ShortcutCatalog.ClosePdf]); // …so Close PDF loses it.
        Assert.Equal("ctrl+l", cleaned[ShortcutCatalog.ClearLog]);
        Assert.Equal(3, cleaned.Count);

        var effective = ShortcutCatalog.Effective(cleaned);
        Assert.Equal("ctrl+e", effective[ShortcutCatalog.Export]);
        Assert.Equal("ctrl+r", effective[ShortcutCatalog.ResetForm]);
        var assigned = effective.Values.Where(g => g.Length > 0).ToList();
        Assert.Equal(assigned.Count, assigned.Distinct().Count());
    }

    [Fact]
    public void Legacy_action_names_map_to_ids()
    {
        Assert.Equal(ShortcutCatalog.ClosePdf, ShortcutCatalog.IdForLegacyName("Close Tab"));
        Assert.Equal(ShortcutCatalog.ResetForm, ShortcutCatalog.IdForLegacyName("Reset"));
        Assert.Equal(ShortcutCatalog.Export, ShortcutCatalog.IdForLegacyName("Export PDFs"));
        Assert.Equal(ShortcutCatalog.FocusFirstPart, ShortcutCatalog.IdForLegacyName("Focus First Part"));
        Assert.Null(ShortcutCatalog.IdForLegacyName("Stress Test"));
    }

    // ───── Settings ─────

    [Fact]
    public async Task Appearance_and_shortcut_settings_round_trip()
    {
        var service = new JsonSettingsService(_paths, new CrashLog(_paths));
        await service.LoadAsync();
        Assert.Equal(AppAccent.Blue, service.Current.Accent);
        Assert.Equal("", service.Current.FontFamily);
        Assert.Equal(AppSettings.DefaultFontSize, service.Current.FontSize);

        service.Update(s =>
        {
            s.Accent = AppAccent.Pink;
            s.FontFamily = "Verdana";
            s.FontSize = 18;
            s.Keybinds[ShortcutCatalog.OpenPdf] = "ctrl+k";
        });
        await service.FlushAsync();
        Assert.Contains("\"accent\": \"pink\"", await File.ReadAllTextAsync(_paths.SettingsFile));

        var reloaded = new JsonSettingsService(_paths, new CrashLog(_paths));
        await reloaded.LoadAsync();
        Assert.Equal(AppAccent.Pink, reloaded.Current.Accent);
        Assert.Equal("Verdana", reloaded.Current.FontFamily);
        Assert.Equal(18, reloaded.Current.FontSize);
        Assert.Equal("ctrl+k", reloaded.Current.Keybinds[ShortcutCatalog.OpenPdf]);
    }

    [Fact]
    public void Cloned_settings_do_not_share_shortcuts()
    {
        var original = new AppSettings();
        var copy = original.Clone();
        copy.Keybinds["quit"] = "ctrl+k";
        Assert.Empty(original.Keybinds);
    }

    [Theory]
    [InlineData(5, AppSettings.MinFontSize)]
    [InlineData(14, 14)]
    [InlineData(99, AppSettings.MaxFontSize)]
    public void Font_size_is_clamped(int input, int expected) =>
        Assert.Equal(expected, AppSettings.ClampFontSize(input));

    // ───── Reset Settings ─────

    [Fact]
    public void Reset_codes_avoid_look_alike_characters()
    {
        var codes = Enumerable.Range(0, 200).Select(_ => SettingsReset.NewCode()).ToList();
        Assert.All(codes, code =>
        {
            Assert.Equal(6, code.Length);
            Assert.DoesNotContain(code, c => "0O1I".Contains(c));
            Assert.All(code, c => Assert.Contains(c, SettingsReset.CodeAlphabet));
        });
        Assert.True(codes.Distinct().Count() > 190);

        Assert.True(SettingsReset.CodeMatches("ABC234", " abc234 "));
        Assert.False(SettingsReset.CodeMatches("ABC234", "ABC235"));
        Assert.False(SettingsReset.CodeMatches("ABC234", ""));
        Assert.False(SettingsReset.CodeMatches("ABC234", null));
    }

    [Fact]
    public async Task Reset_restores_defaults_keeps_what_it_should_and_backs_up_first()
    {
        var settings = new JsonSettingsService(_paths, new CrashLog(_paths));
        await settings.LoadAsync();
        var imported = new DateTimeOffset(2026, 5, 1, 12, 0, 0, TimeSpan.Zero);
        var checkedAt = new DateTimeOffset(2026, 9, 30, 8, 0, 0, TimeSpan.Zero);
        settings.Update(s =>
        {
            s.Theme = AppThemeMode.Dark;
            s.Accent = AppAccent.Green;
            s.FontFamily = "Arial";
            s.FontSize = 20;
            s.ExportFolder = "C:/Exports";
            s.RemoveBlankPages = false;
            s.FolderShortcuts.Add(new FolderShortcut { Label = "Mail", Path = "C:/Mail" });
            s.Keybinds[ShortcutCatalog.OpenPdf] = "ctrl+k";
            s.LegacyImportedUtc = imported;
            s.LastUpdateCheckUtc = checkedAt;
        });

        var workspaces = new WorkspaceStore(_paths);
        await workspaces.LoadAsync();
        var builtIn = workspaces.Catalog.WorkspaceNames.ToList();
        workspaces.Catalog.AddWorkspace("Deposits");
        await workspaces.SaveAsync();

        // Files a reset must never touch.
        await File.WriteAllTextAsync(_paths.LicenseFile, "license");
        await File.WriteAllTextAsync(_paths.ExportHistoryFile, "history");
        await File.WriteAllTextAsync(_paths.SessionsFile, "sessions");

        var changes = 0;
        workspaces.Changed += (_, _) => changes++;
        var backup = await new SettingsReset(_paths, settings, workspaces).ResetAsync();

        // The backup holds the files as they were.
        Assert.StartsWith(Path.Combine(_paths.DataDirectory, "backups"), backup);
        Assert.Contains("C:/Exports", await File.ReadAllTextAsync(Path.Combine(backup, "settings.json")));
        Assert.Contains("Deposits", await File.ReadAllTextAsync(Path.Combine(backup, "workspaces.json")));

        // Settings are back to the defaults, in memory and on disk.
        var current = settings.Current;
        Assert.Equal(AppThemeMode.Light, current.Theme);
        Assert.Equal(AppAccent.Blue, current.Accent);
        Assert.Equal("", current.FontFamily);
        Assert.Equal(AppSettings.DefaultFontSize, current.FontSize);
        Assert.Equal("", current.ExportFolder);
        Assert.True(current.RemoveBlankPages);
        Assert.Empty(current.FolderShortcuts);

        // Kept: shortcuts, the import date, and the update-check time.
        Assert.Equal("ctrl+k", current.Keybinds[ShortcutCatalog.OpenPdf]);
        Assert.Equal(imported, current.LegacyImportedUtc);
        Assert.Equal(checkedAt, current.LastUpdateCheckUtc);

        var reloaded = new JsonSettingsService(_paths, new CrashLog(_paths));
        await reloaded.LoadAsync();
        Assert.Equal("", reloaded.Current.ExportFolder);
        Assert.Equal("ctrl+k", reloaded.Current.Keybinds[ShortcutCatalog.OpenPdf]);

        // Workspaces are the built-in ones again, and listeners were told.
        Assert.Equal(builtIn, workspaces.Catalog.WorkspaceNames);
        Assert.True(changes > 0);
        var reloadedWorkspaces = new WorkspaceStore(_paths);
        await reloadedWorkspaces.LoadAsync();
        Assert.Equal(builtIn, reloadedWorkspaces.Catalog.WorkspaceNames);

        Assert.Equal("license", await File.ReadAllTextAsync(_paths.LicenseFile));
        Assert.Equal("history", await File.ReadAllTextAsync(_paths.ExportHistoryFile));
        Assert.Equal("sessions", await File.ReadAllTextAsync(_paths.SessionsFile));
    }

    // ───── 1.x import ─────

    [Theory]
    [InlineData("Light Blue", AppThemeMode.Light, AppAccent.Blue)]
    [InlineData("Dark Blue", AppThemeMode.Dark, AppAccent.Blue)]
    [InlineData("Dark Green", AppThemeMode.Dark, AppAccent.Green)]
    [InlineData("Light Pink", AppThemeMode.Light, AppAccent.Pink)]
    [InlineData("Dark Pink", AppThemeMode.Dark, AppAccent.Pink)]
    public async Task Legacy_theme_maps_to_mode_and_accent(string theme, AppThemeMode mode, AppAccent accent)
    {
        var settings = await ImportSettingsAsync($$"""{"theme": "{{theme}}"}""");
        Assert.Equal(mode, settings.Theme);
        Assert.Equal(accent, settings.Accent);
    }

    [Fact]
    public async Task Legacy_font_and_shortcuts_are_imported()
    {
        var settings = await ImportSettingsAsync(
            """{"font_family": "Verdana", "font_size": 16}""",
            """
            {"Open PDF": "ctrl+o", "Close Tab": "ctrl+k", "Reset": "ctrl+shift+r", "Clear Log": "ctrl+l",
             "Quit": "ctrl+alt+d", "Stress Test": "ctrl+t"}
            """);

        Assert.Equal("Verdana", settings.FontFamily);
        Assert.Equal(18, settings.FontSize); // 1.x default 12 ↔ 2.x default 14.

        Assert.Equal("ctrl+k", settings.Keybinds[ShortcutCatalog.ClosePdf]);
        Assert.Equal("ctrl+shift+r", settings.Keybinds[ShortcutCatalog.ResetForm]);
        Assert.Equal("ctrl+l", settings.Keybinds[ShortcutCatalog.ClearLog]);
        Assert.Equal(3, settings.Keybinds.Count); // Defaults, reserved, and unknown entries are not stored.
    }

    [Fact]
    public async Task Legacy_defaults_keep_the_built_in_font()
    {
        var settings = await ImportSettingsAsync("""{"font_family": "Segoe UI", "font_size": 12, "theme": "Light Blue"}""");
        Assert.Equal("", settings.FontFamily);
        Assert.Equal(AppSettings.DefaultFontSize, settings.FontSize);
        Assert.Empty(settings.Keybinds);

        var huge = await ImportSettingsAsync("""{"font_size": 32}""");
        Assert.Equal(AppSettings.MaxFontSize, huge.FontSize);
    }

    private async Task<AppSettings> ImportSettingsAsync(string settingsJson, string? keybindsJson = null)
    {
        Directory.CreateDirectory(_paths.LegacyDataDirectory);
        await File.WriteAllTextAsync(Path.Combine(_paths.LegacyDataDirectory, "settings.json"), settingsJson);
        var keybindsFile = Path.Combine(_paths.LegacyDataDirectory, "keybinds.json");
        if (keybindsJson is not null)
        {
            await File.WriteAllTextAsync(keybindsFile, keybindsJson);
        }
        else
        {
            File.Delete(keybindsFile);
        }

        var import = await new LegacyImporter(_paths).ReadAsync();
        var settings = new AppSettings();
        import.ApplySettings!(settings);
        return settings;
    }

    public void Dispose() => _temp.Dispose();
}
