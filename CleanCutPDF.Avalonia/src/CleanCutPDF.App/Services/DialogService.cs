using Avalonia.Controls;
using Avalonia.Layout;
using Avalonia.Media;
using Avalonia.Platform.Storage;

namespace CleanCutPDF.App.Services;

/// <summary>File pickers and message boxes, abstracted so view-models stay testable.</summary>
public interface IDialogService
{
    Task<IReadOnlyList<string>> PickPdfFilesAsync(string title);
    Task<string?> PickFolderAsync(string title);
    Task ShowMessageAsync(string title, string message);
    Task<bool> ConfirmAsync(string title, string message, string confirmText = "OK");
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
        var owner = RequireOwner();
        var files = await owner.StorageProvider.OpenFilePickerAsync(new FilePickerOpenOptions
        {
            Title = title,
            AllowMultiple = true,
            FileTypeFilter = [PdfFiles]
        });
        return files.Select(f => f.TryGetLocalPath()).OfType<string>().ToList();
    }

    public async Task<string?> PickFolderAsync(string title)
    {
        var owner = RequireOwner();
        var folders = await owner.StorageProvider.OpenFolderPickerAsync(new FolderPickerOpenOptions
        {
            Title = title,
            AllowMultiple = false
        });
        return folders.Select(f => f.TryGetLocalPath()).OfType<string>().FirstOrDefault();
    }

    public Task ShowMessageAsync(string title, string message) =>
        ShowDialogAsync(title, message, "OK", cancelText: null);

    public Task<bool> ConfirmAsync(string title, string message, string confirmText = "OK") =>
        ShowDialogAsync(title, message, confirmText, cancelText: "Cancel");

    private async Task<bool> ShowDialogAsync(string title, string message, string confirmText, string? cancelText)
    {
        var owner = RequireOwner();
        var result = false;

        var dialog = new Window
        {
            Title = title,
            Width = 460,
            SizeToContent = SizeToContent.Height,
            CanResize = false,
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

        dialog.Content = new StackPanel
        {
            Margin = new Avalonia.Thickness(20),
            Spacing = 18,
            Children =
            {
                new SelectableTextBlock { Text = message, TextWrapping = TextWrapping.Wrap },
                buttons
            }
        };

        await dialog.ShowDialog(owner);
        return result;
    }

    private Window RequireOwner() =>
        _owner ?? throw new InvalidOperationException("The dialog service has not been attached to a window.");
}
