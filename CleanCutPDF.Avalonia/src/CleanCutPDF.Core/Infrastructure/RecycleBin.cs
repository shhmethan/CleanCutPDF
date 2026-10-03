using System.Runtime.InteropServices;
using System.Text;

namespace CleanCutPDF.Core.Infrastructure;

/// <summary>Moves files to the Recycle Bin (Windows) or Trash (macOS/Linux) instead of deleting them.</summary>
public interface IRecycleBin
{
    /// <summary>Returns null on success, or a short reason it could not be recycled.</summary>
    string? Recycle(string path);
}

public sealed class SystemRecycleBin : IRecycleBin
{
    public string? Recycle(string path)
    {
        try
        {
            if (!File.Exists(path) && !Directory.Exists(path))
            {
                return "it no longer exists";
            }

            if (OperatingSystem.IsWindows())
            {
                return RecycleOnWindows(Path.GetFullPath(path));
            }

            MoveToTrash(Path.GetFullPath(path));
            return null;
        }
        catch (Exception error) when (error is IOException or UnauthorizedAccessException)
        {
            return error.Message;
        }
    }

    // ───── Windows: SHFileOperation with FOF_ALLOWUNDO sends to the Recycle Bin ─────

    private const uint FO_DELETE = 3;
    private const ushort FOF_SILENT = 0x0004;
    private const ushort FOF_NOCONFIRMATION = 0x0010;
    private const ushort FOF_ALLOWUNDO = 0x0040;
    private const ushort FOF_NOERRORUI = 0x0400;

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct SHFILEOPSTRUCT
    {
        public IntPtr hwnd;
        public uint wFunc;
        public string pFrom;
        public string? pTo;
        public ushort fFlags;
        [MarshalAs(UnmanagedType.Bool)] public bool fAnyOperationsAborted;
        public IntPtr hNameMappings;
        public string? lpszProgressTitle;
    }

    [DllImport("shell32.dll", CharSet = CharSet.Unicode)]
    private static extern int SHFileOperation(ref SHFILEOPSTRUCT operation);

    private static string? RecycleOnWindows(string path)
    {
        var operation = new SHFILEOPSTRUCT
        {
            wFunc = FO_DELETE,
            pFrom = path + "\0\0", // double-null-terminated list
            fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
        };
        var result = SHFileOperation(ref operation);
        if (result != 0 || operation.fAnyOperationsAborted)
        {
            return $"Windows could not move it to the Recycle Bin (code {result})";
        }

        return File.Exists(path) || Directory.Exists(path) ? "it is still in place" : null;
    }

    // ───── macOS ~/.Trash, Linux freedesktop trash ─────

    private static void MoveToTrash(string path)
    {
        var home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        var name = Path.GetFileName(path);
        if (OperatingSystem.IsMacOS())
        {
            var trash = Path.Combine(home, ".Trash");
            Directory.CreateDirectory(trash);
            File.Move(path, Unique(trash, name));
            return;
        }

        var files = Path.Combine(home, ".local", "share", "Trash", "files");
        var info = Path.Combine(home, ".local", "share", "Trash", "info");
        Directory.CreateDirectory(files);
        Directory.CreateDirectory(info);
        var target = Unique(files, name);
        File.WriteAllText(Path.Combine(info, Path.GetFileName(target) + ".trashinfo"),
            $"[Trash Info]\nPath={Uri.EscapeDataString(path).Replace("%2F", "/")}\nDeletionDate={DateTime.Now:yyyy-MM-ddTHH:mm:ss}\n",
            Encoding.UTF8);
        File.Move(path, target);
    }

    private static string Unique(string folder, string name)
    {
        var candidate = Path.Combine(folder, name);
        for (var i = 2; File.Exists(candidate) || Directory.Exists(candidate); i++)
        {
            candidate = Path.Combine(folder, $"{Path.GetFileNameWithoutExtension(name)} {i}{Path.GetExtension(name)}");
        }

        return candidate;
    }
}
