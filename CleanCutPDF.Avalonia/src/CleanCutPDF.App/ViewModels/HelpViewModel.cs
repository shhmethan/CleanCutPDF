using CleanCutPDF.App.Services;
using CleanCutPDF.Core;
using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.Services;
using CleanCutPDF.Core.Shortcuts;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace CleanCutPDF.App.ViewModels;

/// <summary>One page of the first-start tour.</summary>
public sealed record TutorialStep(string Title, string Body, AppPage Page);

/// <summary>
/// The tour shown on first start and from Help. It sits beside the main
/// window and switches to the page each step describes, so the page can be
/// seen (and tried) while reading.
/// </summary>
public sealed partial class TutorialViewModel : ObservableObject
{
    private readonly NavigationService _navigation;
    private readonly ISettingsService _settings;

    public TutorialViewModel(NavigationService navigation, ISettingsService settings)
    {
        _navigation = navigation;
        _settings = settings;
    }

    public IReadOnlyList<TutorialStep> Steps { get; } =
    [
        new("Welcome to CleanCutPDF",
            "CleanCutPDF splits a scanned batch into separate documents wherever it finds a SPLIT HERE sheet, and names each file from what you type.\n\n" +
            "This short tour shows where everything is. You can use the app while it is open, and reopen it any time from Help.",
            AppPage.Inbox),
        new("Inbox",
            "Start here. Choose Open PDFs… or drag files onto the window.\n\n" +
            "Folders only organize this list; your files are never moved. Double-click a PDF (or press Enter) to work on it.",
            AppPage.Inbox),
        new("Split & Rename",
            "Each Part is one document from the batch. Type the client name once, fill in the fields for each Part, and check the pages in the preview on the right.\n\n" +
            "Export PDFs saves one named file per Part. Values you type are kept if you close the app.",
            AppPage.SplitRename),
        new("Rename Only",
            "For PDFs that are already separate documents. Add files, fill in the same fields, and each file is renamed (or copied with the new name) without looking for SPLIT HERE sheets.",
            AppPage.RenameOnly),
        new("Quick Split",
            "For batches with one document per client. Drop a PDF and it is split at every SPLIT HERE sheet and saved straight away with numbered names.",
            AppPage.QuickSplit),
        new("Logs",
            "Every file you export or rename is listed here by day and client. Search it, export it, or use Undo Last Export to move the most recent export to the Recycle Bin.",
            AppPage.Logs),
        new("Workspaces",
            "A workspace is a set of fields and a filename format, such as Accounting or Legal. Change the fields, the filename format, or the form layout here, and add your own fields on the Field Library tab.",
            AppPage.Workspaces),
        new("Help and Settings",
            "Help has scanning and printing tips and your keyboard shortcuts. Settings has colors, text size, shortcuts, and updates.\n\n" +
            "When a new version is available, a bar at the top offers Install Update; CleanCutPDF updates itself and reopens.",
            AppPage.Help)
    ];

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(Current), nameof(Progress), nameof(IsFirst), nameof(IsLast), nameof(NextText))]
    public partial int Index { get; private set; }

    public TutorialStep Current => Steps[Index];

    public string Progress => $"Step {Index + 1} of {Steps.Count}";

    public bool IsFirst => Index == 0;

    public bool IsLast => Index == Steps.Count - 1;

    public string NextText => IsLast ? "Done" : "Next";

    public event EventHandler? CloseRequested;

    /// <summary>Called when the tour opens: back to the first step, on its page.</summary>
    public void Start()
    {
        Index = 0;
        _navigation.NavigateTo(Current.Page);
    }

    [RelayCommand]
    private void Next()
    {
        if (IsLast)
        {
            Finish();
            return;
        }

        Index++;
        _navigation.NavigateTo(Current.Page);
    }

    [RelayCommand]
    private void Back()
    {
        if (!IsFirst)
        {
            Index--;
            _navigation.NavigateTo(Current.Page);
        }
    }

    /// <summary>Done, Skip, or closing the window: the tour is not shown automatically again.</summary>
    [RelayCommand]
    public void Finish()
    {
        if (!_settings.Current.TutorialSeen)
        {
            _settings.Update(s => s.TutorialSeen = true);
        }

        CloseRequested?.Invoke(this, EventArgs.Empty);
    }
}

/// <summary>A shortcut as listed on the Help page.</summary>
public sealed record ShortcutLine(string Keys, string Action);

/// <summary>Help page: how to use each mode, scanning tips (from 1.x Help), shortcuts, and troubleshooting.</summary>
public sealed partial class HelpViewModel : ObservableObject
{
    private readonly ToolsService _tools;
    private readonly IDialogService _dialogs;
    private readonly IShellService _shell;
    private readonly TutorialViewModel _tutorial;
    private readonly KeybindsViewModel _keybinds;
    private readonly AppLog _log;

    public HelpViewModel(ToolsService tools, IDialogService dialogs, IShellService shell, TutorialViewModel tutorial,
        KeybindsViewModel keybinds, ISettingsService settings, AppLog log)
    {
        _tools = tools;
        _dialogs = dialogs;
        _shell = shell;
        _tutorial = tutorial;
        _keybinds = keybinds;
        _log = log;
        settings.Changed += (_, _) => OnPropertyChanged(nameof(Shortcuts)); // Shortcuts are edited in Settings.
    }

    public string VersionText => $"{AppInfo.ProductName} {AppInfo.Version}";

    /// <summary>The shortcuts as they are set right now.</summary>
    public IReadOnlyList<ShortcutLine> Shortcuts =>
    [
        .. _keybinds.Rows.Where(r => r.HasGesture).Select(r => new ShortcutLine(ShortcutCatalog.Display(r.Gesture), r.Label)),
        new ShortcutLine(ShortcutCatalog.Display(ShortcutCatalog.DebugConsoleGesture), "Debug Console")
    ];

    [RelayCommand]
    private void ShowTutorial()
    {
        _tutorial.Start();
        _dialogs.ShowTutorial(_tutorial);
    }

    [RelayCommand]
    private Task SaveSplitHereSheetAsync() => _tools.SaveSplitHereTemplateAsync();

    [RelayCommand]
    private async Task OpenLogsFolderAsync()
    {
        Directory.CreateDirectory(_log.Directory);
        if (_shell.OpenFolder(_log.Directory, "Logs folder") is { } error)
        {
            await _dialogs.ShowMessageAsync("Open Folder", error);
        }
    }

    [RelayCommand]
    private void OpenDebugConsole() => _tools.OpenDebugConsole();
}
