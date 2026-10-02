using System.Collections.ObjectModel;
using System.Collections.Specialized;
using CleanCutPDF.App.Services;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace CleanCutPDF.App.ViewModels;

/// <summary>
/// The Inbox file explorer. Phase 1: import (button or drag and drop),
/// multi-select, close, and double-click to open in Split &amp; Rename.
/// Folders, bulk workspace changes, and session restore arrive in Phase 2.
/// </summary>
public sealed partial class InboxViewModel : ObservableObject
{
    private readonly DocumentStore _store;
    private readonly IDialogService _dialogs;
    private readonly ActivityService _activity;
    private readonly NavigationService _navigation;
    private CancellationTokenSource? _importCts;

    public InboxViewModel(DocumentStore store, IDialogService dialogs, ActivityService activity, NavigationService navigation)
    {
        _store = store;
        _dialogs = dialogs;
        _activity = activity;
        _navigation = navigation;

        SelectedDocuments.CollectionChanged += OnSelectionChanged;
        _store.Documents.CollectionChanged += (_, _) => OnPropertyChanged(nameof(IsEmpty));
    }

    public ObservableCollection<DocumentItemViewModel> Documents => _store.Documents;

    public ObservableCollection<DocumentItemViewModel> SelectedDocuments { get; } = [];

    public bool IsEmpty => Documents.Count == 0;

    [ObservableProperty]
    public partial bool IsImporting { get; private set; }

    public string SelectionSummary => SelectedDocuments.Count switch
    {
        0 => "Double-click a PDF to open it. Ctrl/Shift-click to select several.",
        1 => "1 PDF selected",
        var n => $"{n} PDFs selected"
    };

    [RelayCommand]
    private async Task OpenPdfsAsync()
    {
        var paths = await _dialogs.PickPdfFilesAsync("Open PDFs");
        if (paths.Count > 0)
        {
            await ImportAsync(paths);
        }
    }

    /// <summary>Entry point for both the Open button and drag and drop.</summary>
    public async Task ImportAsync(IReadOnlyList<string> paths)
    {
        _importCts ??= new CancellationTokenSource();
        var token = _importCts.Token;
        IsImporting = true;
        try
        {
            var result = await _store.ImportAsync(paths, token);

            var notes = new List<string>();
            if (result.Added > 0)
            {
                notes.Add(result.Added == 1 ? "Added 1 PDF" : $"Added {result.Added} PDFs");
            }

            if (result.Duplicates.Count > 0)
            {
                notes.Add($"already open: {string.Join(", ", result.Duplicates.Take(3))}{(result.Duplicates.Count > 3 ? "…" : "")}");
            }

            if (result.Skipped.Count > 0)
            {
                notes.Add($"skipped {result.Skipped.Count} non-PDF file(s)");
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

    [RelayCommand(CanExecute = nameof(HasSelection))]
    private async Task CloseSelectedAsync()
    {
        var selected = SelectedDocuments.ToList();
        if (selected.Count == 0)
        {
            return;
        }

        var names = string.Join("\n", selected.Take(8).Select(d => d.FileName));
        if (selected.Count > 8)
        {
            names += "\n…";
        }

        var confirmed = await _dialogs.ConfirmAsync(
            "Close PDFs",
            $"Close {selected.Count} selected PDF(s)?\n\n{names}\n\nThe original files on your computer are not changed.",
            "Close");
        if (confirmed)
        {
            _store.Close(selected);
        }
    }

    private bool HasSelection() => SelectedDocuments.Count > 0;

    [RelayCommand]
    private void OpenInEditor(DocumentItemViewModel? document)
    {
        if (document is null || document.IsFailed)
        {
            return;
        }

        _store.ActiveDocument = document;
        _navigation.NavigateTo(AppPage.SplitRename);
    }

    private void OnSelectionChanged(object? sender, NotifyCollectionChangedEventArgs e)
    {
        OnPropertyChanged(nameof(SelectionSummary));
        CloseSelectedCommand.NotifyCanExecuteChanged();
    }
}
