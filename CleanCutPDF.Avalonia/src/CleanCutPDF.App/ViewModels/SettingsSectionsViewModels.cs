using System.Collections.ObjectModel;
using CleanCutPDF.App.Services;
using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.Export;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Models;
using CleanCutPDF.Core.Services;
using CleanCutPDF.Core.Workspaces;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace CleanCutPDF.App.ViewModels;

/// <summary>Folder shortcuts shown as buttons in Split &amp; Rename (1.x Manage Folders…).</summary>
public sealed partial class FolderShortcutsViewModel : ObservableObject
{
    private static readonly IReadOnlyList<string> Icons = ["📁", "📂", "🗂️", "📥", "📤", "📌", "⭐", "⚡", "🧾", "💼"];

    private static readonly IReadOnlyDictionary<string, string> Colors = new Dictionary<string, string>
    {
        ["Default"] = "", ["Blue"] = "#3B8ED0", ["Green"] = "#2E8B57", ["Orange"] = "#E07B24",
        ["Red"] = "#C0392B", ["Purple"] = "#8E44AD", ["Pink"] = "#E75480", ["Gray"] = "#6C757D"
    };

    private readonly ISettingsService _settings;
    private readonly IDialogService _dialogs;
    private readonly IShellService _shell;

    public FolderShortcutsViewModel(ISettingsService settings, IDialogService dialogs, IShellService shell)
    {
        _settings = settings;
        _dialogs = dialogs;
        _shell = shell;
        _settings.Changed += (_, current) => Sync(current);
        Sync(settings.Current);
    }

    public ObservableCollection<FolderShortcut> Shortcuts { get; } = [];

    public bool IsEmpty => Shortcuts.Count == 0;

    private void Sync(AppSettings current)
    {
        Shortcuts.Clear();
        foreach (var shortcut in current.FolderShortcuts)
        {
            Shortcuts.Add(shortcut);
        }

        OnPropertyChanged(nameof(IsEmpty));
    }

    [RelayCommand]
    private async Task AddAsync()
    {
        var folder = await _dialogs.PickFolderAsync("Choose Shortcut Folder");
        if (string.IsNullOrWhiteSpace(folder))
        {
            return;
        }

        var shortcut = await EditAsync(new FolderShortcut { Path = folder, Label = Path.GetFileName(folder.TrimEnd('\\', '/')) });
        if (shortcut is not null)
        {
            _settings.Update(s => s.FolderShortcuts.Add(shortcut));
        }
    }

    [RelayCommand]
    private async Task EditShortcutAsync(FolderShortcut? shortcut)
    {
        if (shortcut is null)
        {
            return;
        }

        var edited = await EditAsync(shortcut with { });
        if (edited is not null)
        {
            _settings.Update(s =>
            {
                var index = s.FolderShortcuts.FindIndex(x => x.Path == shortcut.Path && x.Label == shortcut.Label);
                if (index >= 0)
                {
                    s.FolderShortcuts[index] = edited;
                }
            });
        }
    }

    [RelayCommand]
    private void Remove(FolderShortcut? shortcut)
    {
        if (shortcut is not null)
        {
            _settings.Update(s => s.FolderShortcuts.RemoveAll(x => x.Path == shortcut.Path && x.Label == shortcut.Label));
        }
    }

    [RelayCommand]
    private async Task OpenAsync(FolderShortcut? shortcut)
    {
        if (shortcut is not null && _shell.OpenFolder(shortcut.Path, shortcut.Label) is { } error)
        {
            await _dialogs.ShowMessageAsync("Open Folder", error);
        }
    }

    private async Task<FolderShortcut?> EditAsync(FolderShortcut shortcut)
    {
        var label = await _dialogs.PromptAsync("Folder Shortcut", $"Button name for\n{shortcut.Path}", shortcut.Label, "Next");
        if (string.IsNullOrWhiteSpace(label))
        {
            return null;
        }

        var icon = await _dialogs.ChooseAsync("Folder Shortcut", "Icon:", Icons, shortcut.Icon, "Next");
        if (icon is null)
        {
            return null;
        }

        var currentColor = Colors.FirstOrDefault(c => string.Equals(c.Value, shortcut.Color, StringComparison.OrdinalIgnoreCase)).Key ?? "Default";
        var color = await _dialogs.ChooseAsync("Folder Shortcut", "Button color:", Colors.Keys.ToList(), currentColor, "Save");
        if (color is null)
        {
            return null;
        }

        return shortcut with { Label = label.Trim(), Icon = icon, Color = Colors[color] };
    }
}

/// <summary>One-time, read-only import of CleanCutPDF 1.x workspaces, fields, settings, open PDFs, and history.</summary>
public sealed partial class LegacyImportViewModel(
    LegacyImporter importer,
    WorkspaceStore workspaces,
    ISettingsService settings,
    DocumentStore documents,
    ExportHistory history,
    ClientSuggestions clients,
    IDialogService dialogs,
    ActivityService activity,
    CrashLog crashLog,
    AppLog log) : ObservableObject
{
    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(ImportCommand))]
    public partial bool IsImporting { get; private set; }

    public string LastImportText => settings.Current.LegacyImportedUtc is { } when
        ? $"Last imported {when.ToLocalTime():MMMM d, yyyy h:mm tt}."
        : "Not imported yet.";

    [RelayCommand(CanExecute = nameof(CanImport))]
    private async Task ImportAsync()
    {
        IsImporting = true;
        try
        {
            LegacyImport import;
            using (activity.Begin("Reading CleanCutPDF 1.x data"))
            {
                import = await importer.ReadAsync();
            }

            if (import.Catalog is null && import.Session.Documents.Count == 0 && import.HistoryLines.Count == 0)
            {
                await dialogs.ShowMessageAsync("Import from CleanCutPDF 1.x",
                    "No CleanCutPDF 1.x data was found." + Warnings(import));
                return;
            }

            var again = settings.Current.LegacyImportedUtc is not null
                ? "\n\nYou have imported before. Workspaces and fields with the same names will be replaced again; duplicates are skipped."
                : "";
            if (!await dialogs.ConfirmAsync("Import from CleanCutPDF 1.x",
                    $"Found {import.Summary}.\n\n" +
                    "Imported workspaces and fields replace ones with the same name here; workspaces you created only in this version are kept. " +
                    "Your CleanCutPDF 1.x data is only read, never changed." + again + Warnings(import),
                    "Import"))
            {
                return;
            }

            int added;
            using (activity.Begin("Importing CleanCutPDF 1.x data"))
            {
                if (import.Catalog is not null)
                {
                    workspaces.Catalog.Merge(import.Catalog);
                    await workspaces.SaveAsync();
                }

                settings.Update(s =>
                {
                    import.ApplySettings?.Invoke(s);
                    s.LegacyImportedUtc = DateTimeOffset.UtcNow;
                });

                if (import.HistoryLines.Count > 0)
                {
                    await history.PrependAsync(import.HistoryLines);
                }

                added = await documents.AddSessionAsync(import.Session, workspaces.Catalog.WorkspaceNames.ToHashSet(),
                    replaceFolders: false);
                await clients.RefreshAsync();
                log.Info("Import", $"Imported 1.x data: {import.Summary}; {added} PDF(s) added to the Inbox");
                OnPropertyChanged(nameof(LastImportText));
            }

            // Shown after the busy indicator has stopped.
            await dialogs.ShowMessageAsync("Import Complete",
                $"Imported {import.Summary}.\n\n{added} PDF(s) were added to the Inbox.");
        }
        catch (Exception error)
        {
            crashLog.Write("1.x import failed", error);
            await dialogs.ShowMessageAsync("Import Failed",
                $"The CleanCutPDF 1.x data could not be imported.\n\n{error.Message}\n\nNothing in your 1.x folder was changed.");
        }
        finally
        {
            IsImporting = false;
        }
    }

    private bool CanImport() => !IsImporting;

    private static string Warnings(LegacyImport import) =>
        import.Warnings.Count == 0 ? "" : "\n\nNotes:\n" + string.Join("\n", import.Warnings.Take(8).Select(w => "• " + w));
}
