using System.Diagnostics;

namespace CleanCutPDF.Core.Services;

public interface IShellService
{
    /// <summary>Opens a folder in Explorer/Finder. Returns a user-facing error, or null on success.</summary>
    string? OpenFolder(string? folder, string label = "Folder");

    /// <summary>Opens an https link in the default browser. Returns a user-facing error, or null on success.</summary>
    string? OpenUrl(Uri url);
}

public sealed class ShellService : IShellService
{
    public string? OpenFolder(string? folder, string label = "Folder")
    {
        if (string.IsNullOrWhiteSpace(folder))
        {
            return $"Set the {label.ToLowerInvariant()} first.";
        }

        if (!Directory.Exists(folder))
        {
            return $"{label} no longer exists:\n\n{folder}";
        }

        try
        {
            if (OperatingSystem.IsWindows())
            {
                Process.Start(new ProcessStartInfo("explorer.exe", $"\"{folder}\"") { UseShellExecute = true });
            }
            else if (OperatingSystem.IsMacOS())
            {
                Process.Start("open", [folder]);
            }
            else
            {
                Process.Start("xdg-open", [folder]);
            }

            return null;
        }
        catch (Exception error)
        {
            return $"Could not open this folder:\n\n{error.Message}";
        }
    }

    public string? OpenUrl(Uri url)
    {
        if (url.Scheme != Uri.UriSchemeHttps)
        {
            return "Only secure (https) links can be opened.";
        }

        try
        {
            if (OperatingSystem.IsMacOS())
            {
                Process.Start("open", [url.AbsoluteUri]);
            }
            else if (OperatingSystem.IsWindows())
            {
                Process.Start(new ProcessStartInfo(url.AbsoluteUri) { UseShellExecute = true });
            }
            else
            {
                Process.Start("xdg-open", [url.AbsoluteUri]);
            }

            return null;
        }
        catch (Exception error)
        {
            return $"Could not open your web browser:\n\n{error.Message}\n\n{url}";
        }
    }
}
