using System.ComponentModel;
using CleanCutPDF.App.Services;
using CleanCutPDF.App.ViewModels.Editor;
using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.Export;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Naming;
using CleanCutPDF.Core.Pdf;
using CleanCutPDF.Core.Services;
using CleanCutPDF.Core.Workspaces;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace CleanCutPDF.App.ViewModels;

/// <summary>
/// Split &amp; Rename: shows the active document's Parts with the workspace
/// fields beside a live preview, and exports one PDF per Part.
/// </summary>
public sealed partial class SplitRenameViewModel : ObservableObject
{
    private readonly DocumentStore _store;
    private readonly NavigationService _navigation;
    private readonly WorkspaceStore _workspaces;
    private readonly ISettingsService _settings;
    private readonly IDialogService _dialogs;
    private readonly IShellService _shell;
    private readonly ExportService _export;
    private readonly ClientSuggestions _clients;
    private readonly ToolsService _tools;

    public bool CanUndoLastExport => _tools.CanUndo;

    [RelayCommand]
    private Task UndoLastExportAsync() => _tools.UndoLastExportAsync();
    private readonly ActivityService _activity;
    private readonly CrashLog _crashLog;
    private readonly AppLog _log;
    private DocumentItemViewModel? _formDocument;
    private CancellationTokenSource? _exportCts;
    private bool _syncing;

    public SplitRenameViewModel(DocumentStore store, NavigationService navigation, PagePreviewService previews,
        WorkspaceStore workspaces, ISettingsService settings, IDialogService dialogs, IShellService shell,
        ExportService export, ActivityService activity, CrashLog crashLog, AppLog log, ClientSuggestions clients,
        ToolsService tools)
    {
        _tools = tools;
        _clients = clients;
        _store = store;
        _navigation = navigation;
        _workspaces = workspaces;
        _settings = settings;
        _dialogs = dialogs;
        _shell = shell;
        _export = export;
        _activity = activity;
        _crashLog = crashLog;
        _log = log;
        Preview = new PdfPreviewViewModel(previews, crashLog, log, tools.OpenZoom);
        _store.PropertyChanged += (_, e) =>
        {
            if (e.PropertyName == nameof(DocumentStore.LastExportedFiles))
            {
                OnPropertyChanged(nameof(CanUndoLastExport));
            }
        };

        _store.PropertyChanged += OnStoreChanged;
        _store.CapturingSession += (_, _) => CaptureForm();
        _store.DetectionCompleted += (_, document) =>
        {
            if (ReferenceEquals(document, Document))
            {
                BuildForm();
            }
        };
        _workspaces.Changed += (_, _) =>
        {
            // Workspace or field edits apply to the open PDF right away (values are kept).
            OnPropertyChanged(nameof(WorkspaceNames));
            CaptureForm();
            BuildForm();
        };
        _store.Documents.CollectionChanged += (_, _) => OnPropertyChanged(nameof(OpenDocuments));
        _settings.Changed += (_, current) =>
        {
            _syncing = true;
            MakeClientFolder = current.MakeClientFolder;
            _syncing = false;
            OnPropertyChanged(nameof(FolderShortcuts));
            OnPropertyChanged(nameof(ShowNoSplitWarning));
        };
        MakeClientFolder = _settings.Current.MakeClientFolder;
    }

    public PdfPreviewViewModel Preview { get; }

    public DocumentItemViewModel? Document => _store.ActiveDocument;

    public bool HasDocument => Document is not null;

    /// <summary>Documents that can be opened, for the quick switcher.</summary>
    public IEnumerable<DocumentItemViewModel> OpenDocuments => _store.Documents.Where(d => d.IsReady);

    public DocumentItemViewModel? SwitcherSelection
    {
        get => Document;
        set
        {
            if (value is not null && !ReferenceEquals(value, Document))
            {
                _store.ActiveDocument = value;
            }
        }
    }

    public IReadOnlyList<string> WorkspaceNames => _workspaces.Catalog.WorkspaceNames;

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(Parts))]
    public partial WorkspaceFormViewModel? Form { get; private set; }

    /// <summary>The Parts to show (empty while no form is loaded).</summary>
    public IReadOnlyList<PartViewModel> Parts => Form?.Parts ?? [];

    [ObservableProperty]
    public partial string? SelectedWorkspace { get; set; }

    [ObservableProperty]
    public partial string WorkspaceSummary { get; private set; } = "";

    [ObservableProperty]
    public partial string ClientLabel { get; private set; } = "Client Name (optional):";

    [ObservableProperty]
    public partial string ClientName { get; set; } = "";

    [ObservableProperty]
    public partial bool MakeClientFolder { get; set; } = true;

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(IsFormReady))]
    [NotifyCanExecuteChangedFor(nameof(ExportCommand), nameof(ResetFormCommand))]
    public partial bool IsExporting { get; private set; }

    [ObservableProperty]
    public partial string ExportStatus { get; private set; } = "";

    public bool IsDetecting => Document is { Detection: DetectionState.Running };

    public bool IsFormReady => Form is not null && !IsExporting;

    public bool ShowNoSplitWarning =>
        Document is { NoMarkersFound: true } && _settings.Current.WarnWhenNoSplitMarkers;

    partial void OnSelectedWorkspaceChanged(string? value)
    {
        if (_syncing || value is null || Document is not { } document || value == document.Workspace)
        {
            return;
        }

        CaptureForm();
        _log.Info("Editor", $"{document.FileName}: workspace {document.Workspace} → {value}");
        document.Workspace = value;
        _settings.Update(s => s.DefaultWorkspace = value); // 1.x remembered the last workspace used.
        BuildForm();
        _store.RequestSave();
    }

    [ObservableProperty]
    public partial IReadOnlyList<string> ClientSuggestions { get; private set; } = [];

    public IReadOnlyList<Core.Models.FolderShortcut> FolderShortcuts => _settings.Current.FolderShortcuts;

    [RelayCommand]
    private async Task OpenOutputFolderAsync()
    {
        if (_shell.OpenFolder(_settings.Current.ExportFolder, "Default Export Folder") is { } error)
        {
            await _dialogs.ShowMessageAsync("Open Output Folder", error);
        }
    }

    [RelayCommand]
    private async Task OpenShortcutAsync(Core.Models.FolderShortcut? shortcut)
    {
        if (shortcut is not null && _shell.OpenFolder(shortcut.Path, shortcut.Label) is { } error)
        {
            await _dialogs.ShowMessageAsync("Open Folder", error);
        }
    }

    partial void OnClientNameChanged(string value)
    {
        ClientSuggestions = _syncing ? [] : _clients.Suggest(value);
        if (!_syncing && Document is { } document)
        {
            document.ClientName = value;
            _store.RequestSave();
        }
    }

    partial void OnMakeClientFolderChanged(bool value)
    {
        if (!_syncing)
        {
            _settings.Update(s => s.MakeClientFolder = value);
        }
    }

    /// <summary>The Aa button: normalizes a pasted name such as "JOHN SMITH" to "John Smith".</summary>
    [RelayCommand]
    private void TitleCaseClient() => ClientName = NameCasing.TitleCase(ClientName.Trim().ToLowerInvariant());

    [RelayCommand]
    private async Task DisableNoSplitWarningAsync()
    {
        _settings.Update(s => s.WarnWhenNoSplitMarkers = false);
        await Task.CompletedTask;
    }

    [RelayCommand(CanExecute = nameof(CanEditForm))]
    private async Task ResetFormAsync()
    {
        if (Form is null || !await _dialogs.ConfirmAsync("Reset Form", "Are you sure you want to clear this form?", "Clear"))
        {
            return;
        }

        Form.Reset();
        ClientName = "";
        _activity.Report($"The {Form.Workspace.Name} form has been cleared.");
    }

    private bool CanEditForm() => Form is not null && !IsExporting;

    [RelayCommand]
    private void CloseDocument()
    {
        if (Document is { } document)
        {
            _store.Close([document]);
        }
    }

    [RelayCommand]
    private void BackToInbox() => _navigation.NavigateTo(AppPage.Inbox);

    [RelayCommand]
    private void CancelExport() => _exportCts?.Cancel();

    [RelayCommand(CanExecute = nameof(CanEditForm))]
    private async Task ExportAsync()
    {
        if (Form is null || Document is not { } document)
        {
            return;
        }

        var parts = Form.ToPartInputs();
        var workspace = Form.Workspace;
        var check = ExportValidator.Check(workspace, parts, DateOnly.FromDateTime(DateTime.Today));

        if (check.InvalidValue is not null)
        {
            await _dialogs.ShowMessageAsync("Invalid Field Value", check.InvalidValue);
            return;
        }

        if (check.MissingRequired.Count > 0)
        {
            await _dialogs.ShowMessageAsync("Required Fields Missing",
                "Please fill in the following required field(s) before exporting:\n\n" + Bullets(check.MissingRequired));
            return;
        }

        if (check.BlankOptionalDates.Count > 0 && !await _dialogs.ConfirmAsync("Missing Date",
                "The following date field(s) are blank:\n\n" + Bullets(check.BlankOptionalDates) +
                "\n\nYou can still export; blank dates will be omitted from filenames. Continue?", "Export"))
        {
            return;
        }

        if (check.FutureDates.Count > 0 && _settings.Current.WarnOnFutureDates)
        {
            var (confirmed, dontAsk) = await _dialogs.ConfirmWithOptOutAsync("Confirm Future Date",
                "These dates are in the future. Are you sure?\n\n" + Bullets(check.FutureDates), "Export");
            if (dontAsk)
            {
                _settings.Update(s => s.WarnOnFutureDates = false);
            }

            if (!confirmed)
            {
                return;
            }
        }

        var folder = _settings.Current.ExportFolder;
        if (string.IsNullOrWhiteSpace(folder) || !Directory.Exists(folder))
        {
            folder = await _dialogs.PickFolderAsync("Select Export Folder");
            if (string.IsNullOrWhiteSpace(folder))
            {
                return;
            }
        }

        var request = new ExportRequest(document.FilePath, workspace, ClientName, parts, folder,
            MakeClientFolder, _settings.Current.RemoveBlankPages);
        IsExporting = true;
        ExportStatus = "Preparing…";
        _exportCts = new CancellationTokenSource();
        try
        {
            using var busy = _activity.Begin($"Exporting {document.FileName}");
            var progress = new Progress<ExportProgress>(p => ExportStatus = $"Exporting {p.Stage}…");
            var result = await _export.ExportAsync(request, progress, _exportCts.Token);
            _store.LastExportedFiles = result.Files.Select(f => f.Path).ToList();
            _ = _clients.RefreshAsync();

            var openFolder = await _dialogs.ConfirmAsync("Export Complete",
                $"Exported {result.Files.Count} {workspace.Name} file(s) to:\n{result.OutputFolder}", "Open Folder", "Close");
            if (openFolder && _shell.OpenFolder(result.OutputFolder, "Export folder") is { } error)
            {
                await _dialogs.ShowMessageAsync("Open Folder", error);
            }

            // Like 1.x, a finished document leaves the list.
            _store.Close([document]);
        }
        catch (OperationCanceledException)
        {
            _activity.Report("Export cancelled. No files were kept.");
        }
        catch (Exception error)
        {
            _crashLog.Write($"Export of {document.FileName} failed", error);
            await _dialogs.ShowMessageAsync("Export Failed",
                $"{document.FileName} could not be exported, so no files were kept.\n\n{error.Message}\n\n" +
                "Details were saved to the diagnostic log.");
        }
        finally
        {
            IsExporting = false;
            _exportCts.Dispose();
            _exportCts = null;
        }
    }

    private static string Bullets(IEnumerable<string> items) => string.Join("\n", items.Select(i => "• " + i));

    private void OnStoreChanged(object? sender, PropertyChangedEventArgs e)
    {
        if (e.PropertyName != nameof(DocumentStore.ActiveDocument))
        {
            return;
        }

        CaptureForm();
        if (_formDocument is not null)
        {
            _formDocument.PropertyChanged -= OnDocumentChanged;
        }

        _formDocument = Document;
        if (_formDocument is not null)
        {
            _formDocument.PropertyChanged += OnDocumentChanged;
        }

        _syncing = true;
        ClientName = Document?.ClientName ?? "";
        _syncing = false;

        OnPropertyChanged(nameof(Document));
        OnPropertyChanged(nameof(HasDocument));
        OnPropertyChanged(nameof(OpenDocuments));
        OnPropertyChanged(nameof(SwitcherSelection));
        CloseDocumentCommand.NotifyCanExecuteChanged();
        Preview.ShowDocument(Document);
        BuildForm();
    }

    private void OnDocumentChanged(object? sender, PropertyChangedEventArgs e)
    {
        if (e.PropertyName is nameof(DocumentItemViewModel.Detection) or nameof(DocumentItemViewModel.PagesScanned))
        {
            OnPropertyChanged(nameof(IsDetecting));
            OnPropertyChanged(nameof(ShowNoSplitWarning));
        }
        else if (e.PropertyName == nameof(DocumentItemViewModel.Workspace)
                 && Form is not null && Document is { } document && document.Workspace != Form.Workspace.Name)
        {
            BuildForm(); // Changed from the Inbox (values were captured first).
        }
    }

    /// <summary>Copies what is on screen into the document (before switching or saving).</summary>
    private void CaptureForm()
    {
        if (Form is not null && _formDocument is { } document && document.Workspace == Form.Workspace.Name)
        {
            document.WorkspaceData[Form.Workspace.Name] = Form.Capture();
        }
    }

    private void BuildForm()
    {
        var document = Document;
        if (Form is not null)
        {
            Form.Changed -= OnFormChanged;
        }

        if (document is null || document.Detection is not (DetectionState.Done or DetectionState.Failed))
        {
            Form = null;
            OnPropertyChanged(nameof(IsFormReady));
            OnPropertyChanged(nameof(IsDetecting));
            ExportCommand.NotifyCanExecuteChanged();
            ResetFormCommand.NotifyCanExecuteChanged();
            return;
        }

        var workspace = _workspaces.Catalog.Resolve(document.Workspace);
        if (workspace.Name != document.Workspace)
        {
            document.Workspace = workspace.Name; // The saved workspace no longer exists.
        }

        _syncing = true;
        SelectedWorkspace = workspace.Name;
        _syncing = false;
        WorkspaceSummary = workspace.Summary;
        ClientLabel = $"{workspace.ClientLabel} (optional):";

        document.WorkspaceData.TryGetValue(workspace.Name, out var saved);
        Form = new WorkspaceFormViewModel(workspace, document.Ranges, saved, page => Preview.ShowPage(page),
            DateOnly.FromDateTime(DateTime.Today));
        Form.Changed += OnFormChanged;
        _log.Debug("Editor", $"{document.FileName}: form built with {Form.Parts.Count} part(s)");

        OnPropertyChanged(nameof(IsFormReady));
        OnPropertyChanged(nameof(IsDetecting));
        OnPropertyChanged(nameof(ShowNoSplitWarning));
        ExportCommand.NotifyCanExecuteChanged();
        ResetFormCommand.NotifyCanExecuteChanged();
    }

    private void OnFormChanged(object? sender, EventArgs e) => _store.RequestSave();
}
