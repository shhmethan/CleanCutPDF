using System.Diagnostics;

namespace CleanCutPDF.Core.Services;

public interface IShellService
{
    /// <summary>Opens a folder in Explorer/Finder. Returns a user-facing error, or null on success.</summary>
    string? OpenFolder(string? folder, string label = "Folder");

    /// <summary>Opens an https link in the default browser. Returns a user-facing error, or null on success.</summary>
    string? OpenUrl(Uri url);

    /// <summary>Opens a local file with its default program (PDF viewer, browser for print pages).</summary>
    string? OpenFile(string path);
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
            folder = NormalizeFolder(folder);
            if (OperatingSystem.IsWindows())
            {
                // The folder itself is opened through the shell. "explorer.exe <path>" shows
                // Documents instead when the path has forward slashes (as paths saved by 1.x do)
                // or a comma in a folder name.
                Process.Start(new ProcessStartInfo(folder) { UseShellExecute = true, Verb = "open" });
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

    /// <summary>
    /// The full path with this system's separators and a trailing one, so the shell
    /// can only take it as a folder (never as a program with the same name).
    /// </summary>
    public static string NormalizeFolder(string folder)
    {
        var full = Path.GetFullPath(folder.Trim());
        return Path.EndsInDirectorySeparator(full) ? full : full + Path.DirectorySeparatorChar;
    }

    public string? OpenFile(string path)
    {
        if (!File.Exists(path))
        {
            return $"The file no longer exists:\n\n{path}";
        }

        try
        {
            if (OperatingSystem.IsMacOS())
            {
                Process.Start("open", [path]);
            }
            else if (OperatingSystem.IsWindows())
            {
                Process.Start(new ProcessStartInfo(path) { UseShellExecute = true });
            }
            else
            {
                Process.Start("xdg-open", [path]);
            }

            return null;
        }
        catch (Exception error)
        {
            return $"Could not open the file:\n\n{error.Message}";
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
