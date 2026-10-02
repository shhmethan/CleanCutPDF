namespace CleanCutPDF.Core.Models;

/// <summary>
/// Identifies a specific version of a file on disk. Used to validate cached
/// split ranges and rendered pages (same idea as the Python file_signature).
/// </summary>
public readonly record struct FileSignature(long Size, long LastWriteTicksUtc)
{
    public static FileSignature? TryRead(string path)
    {
        try
        {
            var info = new FileInfo(path);
            return info.Exists ? new FileSignature(info.Length, info.LastWriteTimeUtc.Ticks) : null;
        }
        catch (IOException)
        {
            return null;
        }
        catch (UnauthorizedAccessException)
        {
            return null;
        }
    }
}
