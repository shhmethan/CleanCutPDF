using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Layout;
using Avalonia.Media;
using Avalonia.Platform.Storage;

namespace CleanCutPDF.App.Services;

/// <summary>File pickers and small dialogs, abstracted so view-models stay testable.</summary>
public interface IDialogService
{
    Task<IReadOnlyList<string>> PickPdfFilesAsync(string title);
    Task<string?> PickFolderAsync(string title);
    Task ShowMessageAsync(string title, string message);
    Task<bool> ConfirmAsync(string title, string message, string confirmText = "OK", string cancelText = "Cancel");

    /// <summary>Confirm with a "Don't show this again" checkbox.</summary>
    Task<(bool Confirmed, bool DontAskAgain)> ConfirmWithOptOutAsync(string title, string message, string confirmText,
        string optOutText = "Don't show this again");

    /// <summary>Pick one option from a list. Returns null when cancelled.</summary>
    Task<string?> ChooseAsync(string title, string message, IReadOnlyList<string> options, string? initial,
        string confirmText = "OK");

    /// <summary>Choose where to save a file. Returns null when cancelled.</summary>
    Task<string?> SaveFileAsync(string title, string suggestedName, string extension, string typeName);

    /// <summary>Ask for a line of text. Returns null when cancelled.</summary>
    Task<string?> PromptAsync(string title, string message, string initial = "", string confirmText = "OK");
}

public sealed class WindowDialogService : IDialogService
{
    private static readonly FilePickerFileType PdfFiles = new("PDF files")
    {
        Patterns = ["*.pdf"],
        MimeTypes = ["application/pdf"],
        AppleUniformTypeIdentifiers = ["com.adobe.pdf"]
    };

    private Window? _owner;

    public void Attach(Window owner) => _owner = owner;

    public async Task<IReadOnlyList<string>> PickPdfFilesAsync(string title)
    {
        var files = await RequireOwner().StorageProvider.OpenFilePickerAsync(new FilePickerOpenOptions
        {
            Title = title,
            AllowMultiple = true,
            FileTypeFilter = [PdfFiles]
        });
        return files.Select(f => f.TryGetLocalPath()).OfType<string>().ToList();
    }

    public async Task<string?> PickFolderAsync(string title)
    {
        var folders = await RequireOwner().StorageProvider.OpenFolderPickerAsync(new FolderPickerOpenOptions
        {
            Title = title,
            AllowMultiple = false
        });
        return folders.Select(f => f.TryGetLocalPath()).OfType<string>().FirstOrDefault();
    }

    public async Task<string?> SaveFileAsync(string title, string suggestedName, string extension, string typeName)
    {
        var file = await RequireOwner().StorageProvider.SaveFilePickerAsync(new FilePickerSaveOptions
        {
            Title = title,
            SuggestedFileName = suggestedName,
            DefaultExtension = extension,
            ShowOverwritePrompt = true,
            FileTypeChoices = [new FilePickerFileType(typeName) { Patterns = [$"*.{extension}"] }]
        });
        return file?.TryGetLocalPath();
    }

    public async Task ShowMessageAsync(string title, string message) =>
        await ShowAsync(title, message, "OK", cancelText: null);

    public async Task<bool> ConfirmAsync(string title, string message, string confirmText = "OK",
        string cancelText = "Cancel") =>
        await ShowAsync(title, message, confirmText, cancelText);

    public async Task<(bool Confirmed, bool DontAskAgain)> ConfirmWithOptOutAsync(string title, string message,
        string confirmText, string optOutText = "Don't show this again")
    {
        var optOut = new CheckBox { Content = optOutText };
        var confirmed = await ShowAsync(title, message, confirmText, "Cancel", optOut);
        return (confirmed, confirmed && optOut.IsChecked == true);
    }

    public async Task<string?> ChooseAsync(string title, string message, IReadOnlyList<string> options, string? initial,
        string confirmText = "OK")
    {
        var combo = new ComboBox
        {
            ItemsSource = options,
            SelectedItem = initial is not null && options.Contains(initial) ? initial : options.FirstOrDefault(),
            HorizontalAlignment = HorizontalAlignment.Stretch
        };
        return await ShowAsync(title, message, confirmText, "Cancel", combo) ? combo.SelectedItem as string : null;
    }

    public async Task<string?> PromptAsync(string title, string message, string initial = "", string confirmText = "OK")
    {
        var box = new TextBox { Text = initial };
        box.AttachedToVisualTree += (_, _) =>
        {
            box.Focus();
            box.SelectAll();
        };
        return await ShowAsync(title, message, confirmText, "Cancel", box) ? box.Text?.Trim() : null;
    }

    private async Task<bool> ShowAsync(string title, string message, string confirmText, string? cancelText,
        Control? extra = null)
    {
        var owner = RequireOwner();
        var result = false;
        var dialog = new Window
        {
            Title = title,
            Width = 460,
            SizeToContent = SizeToContent.Height,
            CanResize = false,
            CanMinimize = false,
            CanMaximize = false,
            WindowStartupLocation = WindowStartupLocation.CenterOwner,
            ShowInTaskbar = false
        };

        var confirm = new Button { Content = confirmText, IsDefault = true, MinWidth = 90 };
        confirm.Click += (_, _) =>
        {
            result = true;
            dialog.Close();
        };

        var buttons = new StackPanel
        {
            Orientation = Orientation.Horizontal,
            HorizontalAlignment = HorizontalAlignment.Right,
            Spacing = 8,
            Children = { confirm }
        };
        if (cancelText is not null)
        {
            var cancel = new Button { Content = cancelText, IsCancel = true, MinWidth = 90 };
            cancel.Click += (_, _) => dialog.Close();
            buttons.Children.Add(cancel);
        }

        var body = new StackPanel { Margin = new Avalonia.Thickness(20), Spacing = 14 };
        body.Children.Add(new SelectableTextBlock { Text = message, TextWrapping = TextWrapping.Wrap });
        if (extra is not null)
        {
            body.Children.Add(extra);
        }

        body.Children.Add(buttons);
        dialog.Content = body;
        dialog.KeyDown += (_, e) =>
        {
            if (e.Key == Key.Escape)
            {
                dialog.Close();
            }
        };

        await dialog.ShowDialog(owner);
        return result;
    }

    private Window RequireOwner() =>
        _owner ?? throw new InvalidOperationException("The dialog service has not been attached to a window.");
}
