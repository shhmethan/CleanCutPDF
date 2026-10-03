using System.Collections.ObjectModel;
using System.Collections.Specialized;
using System.ComponentModel;
using CleanCutPDF.App.Services;
using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.Services;
using CleanCutPDF.Core.Sessions;
using CleanCutPDF.Core.Workspaces;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace CleanCutPDF.App.ViewModels;

/// <summary>A folder heading in the explorer list.</summary>
public sealed partial class FolderRowViewModel(FolderViewModel folder) : ObservableObject
{
    public FolderViewModel Folder { get; } = folder;

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(Chevron))]
    public partial bool IsExpanded { get; set; } = true;

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(Heading))]
    public partial int DocumentCount { get; set; }

    public string Chevron => IsExpanded ? "▾" : "▸";
    public string Heading => $"{Folder.Name}  ({DocumentCount})";

    public void RefreshName() => OnPropertyChanged(nameof(Heading));

    public override string ToString() => $"Folder {Folder.Name}, {DocumentCount} PDFs";
}

/// <summary>
/// The Inbox file explorer: folders (Inbox is permanent and first) with their
/// PDFs, multi-select, bulk workspace changes, moving between folders, and
/// double-click / Enter to open. Organizing never moves or renames the real files.
/// </summary>
public sealed partial class InboxViewModel : ObservableObject
{
    private readonly DocumentStore _store;
    private readonly IDialogService _dialogs;
    private readonly ActivityService _activity;
    private readonly NavigationService _navigation;
    private readonly ISettingsService _settings;
    private readonly WorkspaceStore _workspaces;
    private readonly AppLog _log;
    private readonly Dictionary<string, FolderRowViewModel> _folderRows = new();
    private CancellationTokenSource? _importCts;
    private bool _rebuilding;

    public InboxViewModel(DocumentStore store, IDialogService dialogs, ActivityService activity,
        NavigationService navigation, ISettingsService settings, WorkspaceStore workspaces, AppLog log)
    {
        _store = store;
        _dialogs = dialogs;
        _activity = activity;
        _navigation = navigation;
        _settings = settings;
        _workspaces = workspaces;
        _log = log;

        SelectedRows.CollectionChanged += OnSelectionChanged;
        _store.Documents.CollectionChanged += OnDocumentsChanged;
        _store.Folders.CollectionChanged += (_, _) => RebuildRows();
        RebuildRows();
    }

    /// <summary>Folder headings and documents, flattened for a fast virtualized list.</summary>
    public ObservableCollection<object> Rows { get; } = [];

    public ObservableCollection<object> SelectedRows { get; } = [];

    public bool IsEmpty => _store.Documents.Count == 0;

    [ObservableProperty]
    public partial bool IsImporting { get; private set; }

    private IReadOnlyList<DocumentItemViewModel> SelectedDocuments =>
        SelectedRows.OfType<DocumentItemViewModel>()
            .Concat(SelectedRows.OfType<FolderRowViewModel>()
                .SelectMany(row => _store.Documents.Where(d => d.FolderId == row.Folder.Id)))
            .Distinct().ToList();

    private FolderViewModel? SelectedFolder => SelectedRows.OfType<FolderRowViewModel>().FirstOrDefault()?.Folder;

    /// <summary>New PDFs go into the selected folder (or the folder of the selected PDF), like 1.x.</summary>
    private string TargetFolderId =>
        SelectedFolder?.Id
        ?? SelectedRows.OfType<DocumentItemViewModel>().FirstOrDefault()?.FolderId
        ?? SessionFolder.InboxId;

    public string SelectionSummary
    {
        get
        {
            var documents = SelectedRows.OfType<DocumentItemViewModel>().Count();
            return documents switch
            {
                0 when SelectedFolder is { } folder => $"Folder “{folder.Name}” selected",
                0 => "Double-click a PDF (or press Enter) to open it. Ctrl/Shift-click to select several. Right-click for more.",
                1 => "1 PDF selected",
                _ => $"{documents} PDFs selected"
            };
        }
    }

    // ───── Import ─────

    [RelayCommand]
    private async Task OpenPdfsAsync()
    {
        var paths = await _dialogs.PickPdfFilesAsync("Open PDFs");
        if (paths.Count > 0)
        {
            await ImportAsync(paths);
        }
    }

    /// <summary>Entry point for the Open button, drag and drop, and command-line files.</summary>
    public async Task ImportAsync(IReadOnlyList<string> paths)
    {
        var pdfs = paths.Where(DocumentStore.IsPdf).ToList();
        if (pdfs.Count == 0)
        {
            await _dialogs.ShowMessageAsync("Invalid File(s)", "Only PDF files are supported.");
            return;
        }

        // 1.x asked for one workspace for the whole batch when opening several PDFs.
        var workspace = _settings.Current.DefaultWorkspace;
        var names = _workspaces.Catalog.WorkspaceNames;
        if (!names.Contains(workspace))
        {
            workspace = WorkspaceCatalog.AccountingName;
        }

        if (pdfs.Count > 1)
        {
            var chosen = await _dialogs.ChooseAsync($"Open {pdfs.Count} PDFs",
                "Choose the workspace that should be used for all of these files.", names, workspace, "Open Files");
            if (chosen is null)
            {
                return;
            }

            workspace = chosen;
            _settings.Update(s => s.DefaultWorkspace = chosen);
        }

        _importCts ??= new CancellationTokenSource();
        IsImporting = true;
        try
        {
            var result = await _store.ImportAsync(pdfs, workspace, TargetFolderId, _importCts.Token);
            var notes = new List<string>();
            if (result.Added > 0)
            {
                notes.Add(result.Added == 1 ? "Added 1 PDF" : $"Added {result.Added} PDFs");
            }

            if (result.Duplicates.Count > 0)
            {
                notes.Add($"already open: {string.Join(", ", result.Duplicates.Take(3))}{(result.Duplicates.Count > 3 ? "…" : "")}");
            }

            if (paths.Count > pdfs.Count)
            {
                notes.Add($"skipped {paths.Count - pdfs.Count} non-PDF file(s)");
            }

            if (notes.Count > 0)
            {
                _activity.Report(string.Join("; ", notes));
            }
        }
        finally
        {
            if (!_store.Documents.Any(d => d.IsLoading))
            {
                IsImporting = false;
                _importCts?.Dispose();
                _importCts = null;
            }
        }
    }

    [RelayCommand]
    private void CancelImport() => _importCts?.Cancel();

    // ───── Documents ─────

    [RelayCommand]
    public void OpenInEditor(DocumentItemViewModel? document)
    {
        if (document is null || !document.IsReady)
        {
            return;
        }

        _store.ActiveDocument = document;
        _navigation.NavigateTo(AppPage.SplitRename);
    }

    [RelayCommand(CanExecute = nameof(HasDocumentSelection))]
    private async Task CloseSelectedAsync()
    {
        var selected = SelectedDocuments;
        if (selected.Count == 0)
        {
            return;
        }

        var names = string.Join("\n", selected.Take(8).Select(d => d.FileName)) + (selected.Count > 8 ? "\n…" : "");
        if (await _dialogs.ConfirmAsync("Close PDFs",
                $"Close {selected.Count} selected PDF(s)?\n\n{names}\n\nThe original files on your computer are not changed.",
                "Close"))
        {
            _store.Close(selected);
        }
    }

    [RelayCommand(CanExecute = nameof(HasDocumentSelection))]
    private async Task ChangeWorkspaceAsync()
    {
        var selected = SelectedDocuments;
        var names = _workspaces.Catalog.WorkspaceNames;
        var chosen = await _dialogs.ChooseAsync("Change Workspace",
            $"Change workspace for {selected.Count} document(s):", names, selected[0].Workspace, "Apply");
        if (chosen is null)
        {
            return;
        }

        _store.CaptureEditor(); // Keep anything typed under the old workspace.
        foreach (var document in selected)
        {
            document.Workspace = chosen;
        }

        _store.RequestSave();
        _log.Info("Inbox", $"Bulk workspace change: {selected.Count} document(s) → {chosen}");
        _activity.Report($"{selected.Count} document(s) now use {chosen}");
    }

    [RelayCommand(CanExecute = nameof(HasDocumentSelection))]
    private async Task MoveToFolderAsync()
    {
        var selected = SelectedDocuments;
        var names = _store.Folders.Select(f => f.Name).ToList();
        var current = _store.Folders.FirstOrDefault(f => f.Id == selected[0].FolderId)?.Name;
        var chosen = await _dialogs.ChooseAsync("Move Documents", $"Move {selected.Count} document(s) to:", names, current, "Move");
        var folder = _store.Folders.FirstOrDefault(f => f.Name == chosen);
        if (folder is not null)
        {
            _store.MoveToFolder(selected, folder.Id);
            RebuildRows();
        }
    }

    private bool HasDocumentSelection() => SelectedDocuments.Count > 0;

    // ───── Folders ─────

    [RelayCommand]
    private async Task NewFolderAsync()
    {
        var name = await _dialogs.PromptAsync("New Folder", "Folder name:", "", "Create");
        if (string.IsNullOrWhiteSpace(name))
        {
            return;
        }

        if (_store.FolderNameExists(name))
        {
            await _dialogs.ShowMessageAsync("Folder Exists", $"A folder named “{name}” already exists.");
            return;
        }

        var folder = _store.CreateFolder(name);
        Select(_folderRows[folder.Id]);
    }

    [RelayCommand(CanExecute = nameof(CanEditFolder))]
    private async Task RenameFolderAsync()
    {
        if (SelectedFolder is not { IsInbox: false } folder)
        {
            return;
        }

        var name = await _dialogs.PromptAsync("Rename Folder", "New folder name:", folder.Name, "Rename");
        if (string.IsNullOrWhiteSpace(name) || name == folder.Name)
        {
            return;
        }

        if (_store.FolderNameExists(name, folder.Id))
        {
            await _dialogs.ShowMessageAsync("Folder Exists", $"A folder named “{name}” already exists.");
            return;
        }

        _store.RenameFolder(folder, name);
        _folderRows[folder.Id].RefreshName();
    }

    [RelayCommand(CanExecute = nameof(CanEditFolder))]
    private async Task DeleteFolderAsync()
    {
        if (SelectedFolder is not { IsInbox: false } folder)
        {
            return;
        }

        var count = _store.Documents.Count(d => d.FolderId == folder.Id);
        if (await _dialogs.ConfirmAsync("Delete Folder",
                $"Delete the folder “{folder.Name}”?\n\n{count} PDF(s) inside it will be moved to Inbox.\n" +
                "The original PDF files on your computer will not be deleted.", "Delete Folder"))
        {
            _store.DeleteFolder(folder);
        }
    }

    [RelayCommand(CanExecute = nameof(CanEditFolder))]
    private void MoveFolderUp() => MoveSelectedFolder(-1);

    [RelayCommand(CanExecute = nameof(CanEditFolder))]
    private void MoveFolderDown() => MoveSelectedFolder(+1);

    private bool CanEditFolder() => SelectedFolder is { IsInbox: false };

    private void MoveSelectedFolder(int direction)
    {
        if (SelectedFolder is { } folder)
        {
            _store.MoveFolder(folder, direction);
            Select(_folderRows[folder.Id]);
        }
    }

    [RelayCommand]
    private void ToggleFolder(FolderRowViewModel? row)
    {
        if (row is not null)
        {
            row.IsExpanded = !row.IsExpanded;
            RebuildRows();
        }
    }

    // ───── Rows ─────

    private void OnDocumentsChanged(object? sender, NotifyCollectionChangedEventArgs e)
    {
        foreach (DocumentItemViewModel item in e.NewItems ?? Array.Empty<DocumentItemViewModel>())
        {
            item.PropertyChanged += OnDocumentPropertyChanged;
        }

        foreach (DocumentItemViewModel item in e.OldItems ?? Array.Empty<DocumentItemViewModel>())
        {
            item.PropertyChanged -= OnDocumentPropertyChanged;
        }

        if (e.Action == NotifyCollectionChangedAction.Reset)
        {
            foreach (var item in _store.Documents)
            {
                item.PropertyChanged -= OnDocumentPropertyChanged;
                item.PropertyChanged += OnDocumentPropertyChanged;
            }
        }

        OnPropertyChanged(nameof(IsEmpty));
        RebuildRows();
    }

    private void OnDocumentPropertyChanged(object? sender, PropertyChangedEventArgs e)
    {
        if (e.PropertyName == nameof(DocumentItemViewModel.FolderId))
        {
            RebuildRows();
        }
    }

    private void RebuildRows()
    {
        var keep = SelectedRows.ToList();
        _rebuilding = true;
        try
        {
            Rows.Clear();
            foreach (var folder in _store.Folders)
            {
                if (!_folderRows.TryGetValue(folder.Id, out var row) || !ReferenceEquals(row.Folder, folder))
                {
                    row = _folderRows[folder.Id] = new FolderRowViewModel(folder);
                }

                var documents = _store.Documents.Where(d => d.FolderId == folder.Id).ToList();
                row.DocumentCount = documents.Count;
                Rows.Add(row);
                if (row.IsExpanded)
                {
                    foreach (var document in documents)
                    {
                        Rows.Add(document);
                    }
                }
            }

            SelectedRows.Clear();
            foreach (var item in keep.Where(Rows.Contains))
            {
                SelectedRows.Add(item);
            }
        }
        finally
        {
            _rebuilding = false;
        }

        OnSelectionChanged(this, new NotifyCollectionChangedEventArgs(NotifyCollectionChangedAction.Reset));
    }

    private void Select(object row)
    {
        SelectedRows.Clear();
        if (Rows.Contains(row))
        {
            SelectedRows.Add(row);
        }
    }

    private void OnSelectionChanged(object? sender, NotifyCollectionChangedEventArgs e)
    {
        if (_rebuilding)
        {
            return;
        }

        OnPropertyChanged(nameof(SelectionSummary));
        CloseSelectedCommand.NotifyCanExecuteChanged();
        ChangeWorkspaceCommand.NotifyCanExecuteChanged();
        MoveToFolderCommand.NotifyCanExecuteChanged();
        RenameFolderCommand.NotifyCanExecuteChanged();
        DeleteFolderCommand.NotifyCanExecuteChanged();
        MoveFolderUpCommand.NotifyCanExecuteChanged();
        MoveFolderDownCommand.NotifyCanExecuteChanged();
    }
}
