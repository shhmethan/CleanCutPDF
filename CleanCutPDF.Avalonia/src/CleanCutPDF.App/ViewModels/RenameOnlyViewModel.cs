using System.Collections.ObjectModel;
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

/// <summary>A PDF waiting to be renamed.</summary>
public sealed partial class RenameFileViewModel(string filePath, string workspace) : ObservableObject, IPreviewDocument
{
    public string FilePath { get; } = filePath;
    public string FileName { get; } = Path.GetFileName(filePath);

    [ObservableProperty]
    public partial int PageCount { get; set; }

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(StatusText))]
    public partial string? Error { get; set; }

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(StatusText))]
    public partial bool IsLoaded { get; set; }

    public string Workspace { get; set; } = workspace;
    public string ClientName { get; set; } = "";
    public Dictionary<string, List<Dictionary<string, string>>> WorkspaceData { get; } = new();

    public string StatusText => Error ?? (IsLoaded ? (PageCount == 1 ? "1 page" : $"{PageCount} pages") : "Loading…");

    public override string ToString() => $"{FileName}, {StatusText}";
}

/// <summary>
/// Rename Only: each PDF is one complete document (no SPLIT HERE markers),
/// named with the normal workspace fields and filename template. Either a
/// renamed copy goes to the output folder, or the original is renamed in place.
/// </summary>
public sealed partial class RenameOnlyViewModel : ObservableObject
{
    public const string CopyAction = "Create renamed copies";
    public const string InPlaceAction = "Rename originals in place";

    private readonly IPdfEngine _engine;
    private readonly PagePreviewService _previews;
    private readonly WorkspaceStore _workspaces;
    private readonly ISettingsService _settings;
    private readonly IDialogService _dialogs;
    private readonly RenameService _rename;
    private readonly ClientSuggestions _clients;
    private readonly ActivityService _activity;
    private readonly CrashLog _crashLog;
    private readonly AppLog _log;
    private RenameFileViewModel? _formFile;
    private bool _syncing;

    public RenameOnlyViewModel(IPdfEngine engine, PagePreviewService previews, WorkspaceStore workspaces,
        ISettingsService settings, IDialogService dialogs, RenameService rename, ClientSuggestions clients,
        ActivityService activity, CrashLog crashLog, AppLog log)
    {
        _engine = engine;
        _previews = previews;
        _workspaces = workspaces;
        _settings = settings;
        _dialogs = dialogs;
        _rename = rename;
        _clients = clients;
        _activity = activity;
        _crashLog = crashLog;
        _log = log;
        Preview = new PdfPreviewViewModel(previews, crashLog, log);
        OutputFolder = settings.Current.ExportFolder;
        var lastExportFolder = OutputFolder;
        settings.Changed += (_, current) =>
        {
            // Follow the default export folder unless the user picked a different one here.
            if (string.IsNullOrWhiteSpace(OutputFolder) || OutputFolder == lastExportFolder)
            {
                OutputFolder = current.ExportFolder;
            }

            lastExportFolder = current.ExportFolder;
        };
        _workspaces.Changed += (_, _) =>
        {
            OnPropertyChanged(nameof(WorkspaceNames));
            CaptureForm();
            BuildForm();
        };
    }

    public ObservableCollection<RenameFileViewModel> Files { get; } = [];

    public PdfPreviewViewModel Preview { get; }

    public IReadOnlyList<string> WorkspaceNames => _workspaces.Catalog.WorkspaceNames;

    public IReadOnlyList<string> Actions { get; } = [CopyAction, InPlaceAction];

    public bool HasFiles => Files.Count > 0;

    [ObservableProperty]
    public partial RenameFileViewModel? SelectedFile { get; set; }

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(Parts))]
    public partial WorkspaceFormViewModel? Form { get; private set; }

    /// <summary>The Parts to show (empty while no form is loaded).</summary>
    public IReadOnlyList<PartViewModel> Parts => Form?.Parts ?? [];

    [ObservableProperty]
    public partial string? SelectedWorkspace { get; set; }

    [ObservableProperty]
    public partial string ClientLabel { get; private set; } = "Client Name (optional):";

    [ObservableProperty]
    public partial string ClientName { get; set; } = "";

    [ObservableProperty]
    public partial IReadOnlyList<string> ClientSuggestions { get; private set; } = [];

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(IsCopy))]
    public partial string SelectedAction { get; set; } = CopyAction;

    public bool IsCopy => SelectedAction == CopyAction;

    [ObservableProperty]
    public partial string OutputFolder { get; set; } = "";

    [ObservableProperty]
    public partial string ProposedName { get; private set; } = "";

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(RenameCommand))]
    public partial bool IsBusy { get; private set; }

    // ───── Files ─────

    [RelayCommand]
    private async Task AddPdfsAsync()
    {
        var paths = await _dialogs.PickPdfFilesAsync("Add PDFs to Rename");
        await AddFilesAsync(paths);
    }

    /// <summary>Also used when PDFs are dropped while this page is showing.</summary>
    public async Task AddFilesAsync(IReadOnlyList<string> paths)
    {
        var workspace = _workspaces.Catalog.WorkspaceNames.Contains(_settings.Current.DefaultWorkspace)
            ? _settings.Current.DefaultWorkspace
            : WorkspaceCatalog.AccountingName;
        var added = new List<RenameFileViewModel>();
        foreach (var path in paths.Where(DocumentStore.IsPdf).Select(Path.GetFullPath))
        {
            if (Files.Any(f => string.Equals(f.FilePath, path, StringComparison.OrdinalIgnoreCase)))
            {
                continue;
            }

            var file = new RenameFileViewModel(path, workspace);
            Files.Add(file);
            added.Add(file);
        }

        OnPropertyChanged(nameof(HasFiles));
        SelectedFile ??= added.FirstOrDefault();
        foreach (var file in added)
        {
            try
            {
                file.PageCount = (await _engine.OpenAsync(file.FilePath)).PageCount;
                file.IsLoaded = true;
            }
            catch (PdfOpenException error)
            {
                file.Error = error.Message;
            }
            catch (Exception error)
            {
                _crashLog.Write($"Rename Only: opening {file.FileName} failed", error);
                file.Error = "Could not be opened. Details were saved to the log.";
            }

            if (ReferenceEquals(file, SelectedFile))
            {
                BuildForm();
                Preview.ShowDocument(null);
                Preview.ShowDocument(file);
            }
        }

        if (added.Count > 0)
        {
            _log.Info("Rename", $"Added {added.Count} PDF(s) to Rename Only");
        }
    }

    [RelayCommand]
    private void Remove(RenameFileViewModel? file)
    {
        if (file is null)
        {
            return;
        }

        var index = Files.IndexOf(file);
        Files.Remove(file);
        OnPropertyChanged(nameof(HasFiles));
        if (ReferenceEquals(SelectedFile, file))
        {
            SelectedFile = Files.Count == 0 ? null : Files[Math.Min(index, Files.Count - 1)];
        }
    }

    [RelayCommand]
    private void Clear()
    {
        Files.Clear();
        SelectedFile = null;
        OnPropertyChanged(nameof(HasFiles));
    }

    [RelayCommand]
    private async Task BrowseOutputAsync()
    {
        var folder = await _dialogs.PickFolderAsync("Select Rename Output Folder");
        if (!string.IsNullOrWhiteSpace(folder))
        {
            OutputFolder = folder;
        }
    }

    [RelayCommand]
    private void TitleCaseClient() => ClientName = NameCasing.TitleCase(ClientName.Trim().ToLowerInvariant());

    // ───── Rename ─────

    [RelayCommand(CanExecute = nameof(CanRename))]
    private async Task RenameAsync()
    {
        if (Form is null || SelectedFile is not { IsLoaded: true } file)
        {
            await _dialogs.ShowMessageAsync("Rename PDF", "Select a PDF first.");
            return;
        }

        var parts = Form.ToPartInputs();
        var check = ExportValidator.Check(Form.Workspace, parts, DateOnly.FromDateTime(DateTime.Today), "File");
        if (check.InvalidValue is not null)
        {
            await _dialogs.ShowMessageAsync("Invalid Field Value", check.InvalidValue);
            return;
        }

        if (check.MissingRequired.Count > 0)
        {
            await _dialogs.ShowMessageAsync("Required Fields Missing",
                "Please fill in the following required field(s):\n\n" + string.Join("\n", check.MissingRequired.Select(m => "• " + m)));
            return;
        }

        if (check.FutureDates.Count > 0 && _settings.Current.WarnOnFutureDates)
        {
            var (confirmed, dontAsk) = await _dialogs.ConfirmWithOptOutAsync("Confirm Future Date",
                "This date is in the future. Are you sure?\n\n" + string.Join("\n", check.FutureDates.Select(m => "• " + m)), "Rename");
            if (dontAsk)
            {
                _settings.Update(s => s.WarnOnFutureDates = false);
            }

            if (!confirmed)
            {
                return;
            }
        }

        var mode = IsCopy ? RenameMode.CreateCopy : RenameMode.RenameInPlace;
        if (mode == RenameMode.CreateCopy && string.IsNullOrWhiteSpace(OutputFolder))
        {
            await _dialogs.ShowMessageAsync("Output Folder Required", "Choose an output folder first.");
            return;
        }

        if (mode == RenameMode.RenameInPlace &&
            !await _dialogs.ConfirmAsync("Rename Original", $"This will change the original filename of\n{file.FileName}\n\nContinue?", "Rename"))
        {
            return;
        }

        IsBusy = true;
        try
        {
            var result = await _rename.RenameAsync(new RenameRequest(file.FilePath, Form.Workspace, ClientName,
                parts[0].Values, file.PageCount, mode, OutputFolder));
            if (mode == RenameMode.RenameInPlace)
            {
                await _previews.ForgetDocumentAsync(file.FilePath);
            }

            _activity.Report($"Saved as {Path.GetFileName(result.TargetPath)}");
            _ = _clients.RefreshAsync();
            Remove(file);
        }
        catch (Exception error)
        {
            _crashLog.Write($"Rename of {file.FileName} failed", error);
            await _dialogs.ShowMessageAsync("Rename Failed", $"{file.FileName} could not be renamed.\n\n{error.Message}");
        }
        finally
        {
            IsBusy = false;
        }
    }

    private bool CanRename() => !IsBusy;

    // ───── Form ─────

    partial void OnSelectedFileChanged(RenameFileViewModel? value)
    {
        CaptureForm();
        _syncing = true;
        ClientName = value?.ClientName ?? "";
        _syncing = false;
        Preview.ShowDocument(value is { IsLoaded: true } ? value : null);
        BuildForm();
    }

    partial void OnSelectedWorkspaceChanged(string? value)
    {
        if (_syncing || value is null || SelectedFile is not { } file || value == file.Workspace)
        {
            return;
        }

        CaptureForm();
        file.Workspace = value;
        _settings.Update(s => s.DefaultWorkspace = value);
        BuildForm();
    }

    partial void OnClientNameChanged(string value)
    {
        if (!_syncing && SelectedFile is { } file)
        {
            file.ClientName = value;
        }

        ClientSuggestions = _clients.Suggest(value);
        UpdateProposedName();
    }

    partial void OnSelectedActionChanged(string value) => UpdateProposedName();

    private void CaptureForm()
    {
        if (Form is not null && _formFile is { } file && file.Workspace == Form.Workspace.Name)
        {
            file.WorkspaceData[Form.Workspace.Name] = Form.Capture();
        }
    }

    private void BuildForm()
    {
        if (Form is not null)
        {
            Form.Changed -= OnFormChanged;
        }

        _formFile = SelectedFile;
        if (SelectedFile is not { IsLoaded: true } file)
        {
            Form = null;
            ProposedName = "";
            return;
        }

        var workspace = _workspaces.Catalog.Resolve(file.Workspace);
        file.Workspace = workspace.Name;
        _syncing = true;
        SelectedWorkspace = workspace.Name;
        _syncing = false;
        ClientLabel = $"{workspace.ClientLabel} (optional):";
        file.WorkspaceData.TryGetValue(workspace.Name, out var saved);
        Form = new WorkspaceFormViewModel(workspace, [new PageRange(0, Math.Max(0, file.PageCount - 1))], saved,
            page => Preview.ShowPage(page), DateOnly.FromDateTime(DateTime.Today), "File");
        Form.Changed += OnFormChanged;
        UpdateProposedName();
    }

    private void OnFormChanged(object? sender, EventArgs e) => UpdateProposedName();

    private void UpdateProposedName()
    {
        if (Form is null)
        {
            ProposedName = "";
            return;
        }

        try
        {
            var name = RenameService.ProposedName(Form.Workspace, ClientName, Form.Parts[0].Values());
            ProposedName = IsCopy ? $"Will be saved as: {name}" : $"Will be renamed to: {name}";
        }
        catch (FormatException error)
        {
            ProposedName = error.Message;
        }
    }
}
