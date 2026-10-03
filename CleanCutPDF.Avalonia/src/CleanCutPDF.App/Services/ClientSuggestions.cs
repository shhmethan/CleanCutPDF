using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.Export;
using CleanCutPDF.Core.Services;

namespace CleanCutPDF.App.Services;

/// <summary>
/// Client-name suggestions for the client field. The index is built in the
/// background (export folder subfolders + export history) and refreshed after
/// exports or when the export folder changes; typing only searches memory.
/// </summary>
public sealed class ClientSuggestions
{
    private readonly ClientNameIndex _index;
    private readonly ISettingsService _settings;
    private readonly AppLog _log;
    private string? _lastFolder;

    public ClientSuggestions(ClientNameIndex index, ISettingsService settings, AppLog log)
    {
        _index = index;
        _settings = settings;
        _log = log;
        _settings.Changed += (_, current) =>
        {
            if (current.ExportFolder != _lastFolder)
            {
                _ = RefreshAsync();
            }
        };
    }

    public IReadOnlyList<string> Suggest(string? text) => _index.Suggest(text);

    public async Task RefreshAsync()
    {
        _lastFolder = _settings.Current.ExportFolder;
        try
        {
            await _index.RefreshAsync(_lastFolder);
            _log.Debug("Clients", $"Suggestion index has {_index.Names.Count} name(s)");
        }
        catch (Exception error)
        {
            _log.Warning("Clients", "Client suggestions could not be refreshed", error);
        }
    }
}
