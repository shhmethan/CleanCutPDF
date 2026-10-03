using CleanCutPDF.App.Services;
using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.Models;
using CleanCutPDF.Core.Services;
using CleanCutPDF.Core.Shortcuts;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace CleanCutPDF.App.ViewModels;

/// <summary>One action and its shortcut in the Settings list.</summary>
public sealed partial class KeybindRowViewModel(ShortcutAction action) : ObservableObject
{
    public ShortcutAction Action { get; } = action;

    public string Label => Action.Label;

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(ButtonText), nameof(HasGesture))]
    public partial string Gesture { get; set; } = action.DefaultGesture;

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(ButtonText))]
    public partial bool IsCapturing { get; set; }

    public string ButtonText => IsCapturing ? "Press keys…" : ShortcutCatalog.Display(Gesture);

    public bool HasGesture => Gesture.Length > 0;

    // Used as the accessible name read by screen readers.
    public override string ToString() => $"{Label}: {ShortcutCatalog.Display(Gesture)}";
}

/// <summary>
/// Keyboard shortcuts: the list in Settings (press-to-capture, conflict
/// checks, reset) and the lookup the main window uses for key presses.
/// </summary>
public sealed partial class KeybindsViewModel : ObservableObject
{
    private readonly ISettingsService _settings;
    private readonly IDialogService _dialogs;
    private readonly AppLog _log;
    private IReadOnlyDictionary<string, string> _overrides = new Dictionary<string, string>();
    private KeybindRowViewModel? _capturing;

    public KeybindsViewModel(ISettingsService settings, IDialogService dialogs, AppLog log)
    {
        _settings = settings;
        _dialogs = dialogs;
        _log = log;
        Rows = ShortcutCatalog.Actions.Select(a => new KeybindRowViewModel(a)).ToList();
        _settings.Changed += (_, current) => Sync(current);
        Sync(_settings.Current);
    }

    public IReadOnlyList<KeybindRowViewModel> Rows { get; }

    /// <summary>Why the last attempt was refused (empty when fine).</summary>
    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(HasMessage))]
    public partial string Message { get; private set; } = "";

    public bool HasMessage => Message.Length > 0;

    /// <summary>True while Settings is waiting for a key combination; shortcuts are paused.</summary>
    public bool IsCapturing => _capturing is not null;

    /// <summary>The action id a key press should run, or null.</summary>
    public string? Match(string gesture) => IsCapturing ? null : ShortcutCatalog.Match(_overrides, gesture);

    [RelayCommand]
    private void BeginCapture(KeybindRowViewModel? row)
    {
        CancelCapture();
        if (row is null)
        {
            return;
        }

        Message = "";
        _capturing = row;
        row.IsCapturing = true;
    }

    public void CancelCapture()
    {
        if (_capturing is { } row)
        {
            row.IsCapturing = false;
            _capturing = null;
        }
    }

    /// <summary>Called by the view with the combination that was pressed during capture.</summary>
    public void Capture(string gesture)
    {
        if (_capturing is not { } row)
        {
            return;
        }

        CancelCapture();
        if (ShortcutCatalog.Validate(_overrides, row.Action.Id, gesture) is { } problem)
        {
            Message = problem;
            return;
        }

        Save(ShortcutCatalog.Assign(_overrides, row.Action.Id, gesture));
        _log.Info("Shortcuts", $"{row.Label} → {ShortcutCatalog.Normalize(gesture)}");
    }

    [RelayCommand]
    private void Clear(KeybindRowViewModel? row)
    {
        CancelCapture();
        if (row is not null)
        {
            Message = "";
            Save(ShortcutCatalog.Assign(_overrides, row.Action.Id, ""));
            _log.Info("Shortcuts", $"{row.Label} → (none)");
        }
    }

    [RelayCommand]
    private async Task ResetAllAsync()
    {
        CancelCapture();
        if (await _dialogs.ConfirmAsync("Keyboard Shortcuts", "Reset every keyboard shortcut to its default?", "Reset"))
        {
            Message = "";
            Save(new Dictionary<string, string>());
            _log.Info("Shortcuts", "Reset to defaults");
        }
    }

    /// <summary>The 1.x "Show Keybinds" list.</summary>
    [RelayCommand]
    private Task ShowAllAsync()
    {
        CancelCapture();
        var lines = Rows.Where(r => r.HasGesture).Select(r => $"{ShortcutCatalog.Display(r.Gesture)}  —  {r.Label}")
            .Append($"{ShortcutCatalog.Display(ShortcutCatalog.DebugConsoleGesture)}  —  Debug Console");
        return _dialogs.ShowMessageAsync("Keyboard Shortcuts", string.Join("\n", lines));
    }

    private void Save(Dictionary<string, string> overrides) => _settings.Update(s => s.Keybinds = overrides);

    private void Sync(AppSettings current)
    {
        _overrides = ShortcutCatalog.Clean(current.Keybinds);
        var effective = ShortcutCatalog.Effective(_overrides);
        foreach (var row in Rows)
        {
            row.Gesture = effective[row.Action.Id];
        }
    }
}
