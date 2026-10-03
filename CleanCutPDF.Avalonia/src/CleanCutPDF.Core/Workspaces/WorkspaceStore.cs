using System.Text.Json;
using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.Infrastructure;

namespace CleanCutPDF.Core.Workspaces;

/// <summary>Loads and saves workspaces.json (field library + workspaces).</summary>
public sealed class WorkspaceStore(AppPaths paths, AppLog? log = null)
{
    internal static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower
    };

    public WorkspaceCatalog Catalog { get; private set; } = WorkspaceCatalog.CreateDefault();

    public event EventHandler? Changed;

    public async Task LoadAsync(CancellationToken cancellationToken = default)
    {
        var catalog = WorkspaceCatalog.CreateDefault();
        try
        {
            if (File.Exists(paths.WorkspacesFile))
            {
                await using var stream = File.OpenRead(paths.WorkspacesFile);
                catalog = await JsonSerializer.DeserializeAsync<WorkspaceCatalog>(stream, JsonOptions, cancellationToken)
                          ?? catalog;
            }
        }
        catch (JsonException error)
        {
            log?.Error("Workspaces", "workspaces.json was unreadable; built-in workspaces are used", error);
            try
            {
                File.Copy(paths.WorkspacesFile, paths.WorkspacesFile + $".corrupt-{DateTime.Now:yyyyMMddHHmmss}");
            }
            catch
            {
                // Best effort.
            }
        }

        catalog.Normalize();
        Catalog = catalog;
        log?.Info("Workspaces", $"Loaded {catalog.Workspaces.Count} workspace(s), {catalog.Fields.Count} field(s)");
        Changed?.Invoke(this, EventArgs.Empty);
    }

    public async Task SaveAsync(CancellationToken cancellationToken = default)
    {
        Catalog.Normalize();
        await AtomicFile.WriteAllTextAsync(paths.WorkspacesFile, JsonSerializer.Serialize(Catalog, JsonOptions), cancellationToken);
        Changed?.Invoke(this, EventArgs.Empty);
    }
}
