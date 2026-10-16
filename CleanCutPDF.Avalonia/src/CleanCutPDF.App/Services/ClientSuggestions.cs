using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.Export;
using CleanCutPDF.Core.Services;

namespace CleanCutPDF.App.Services;

/// <summary>
/// Client-name suggestions for the client field. The index is built in the
/// background from the export history (the Logs page) and refreshed whenever
/// the history changes; typing only searches memory. Names the user hid
/// (Logs › right-click, or Settings) are left out until they are exported again.
/// </summary>
public sealed class ClientSuggestions
{
    private readonly ClientNameIndex _index;
    private readonly ISettingsService? _settings;
    private readonly AppLog _log;

    public ClientSuggestions(ClientNameIndex index, ExportHistory history, AppLog log, ISettingsService? settings = null)
    {
        _index = index;
        _settings = settings;
        _log = log;
        history.Changed += (_, _) => _ = RefreshAsync(); // Exports, renames, Undo, Clear Log, 1.x import.
    }

    /// <summary>Every client name in the export history, newest first (hidden ones included).</summary>
    public IReadOnlyList<string> KnownNames => _index.Names;

    public IReadOnlyList<string> Suggest(string? text) =>
        _index.Suggest(text, ClientNameIndex.DefaultLimit, _settings?.Current.HiddenClientNames);

    /// <summary>Hidden names, A → Z (for Settings).</summary>
    public IReadOnlyList<string> HiddenNames =>
        _settings is null ? [] : _settings.Current.HiddenClientNames.Keys.Order(StringComparer.OrdinalIgnoreCase).ToList();

    /// <summary>Stops suggesting a name. The export history is not changed.</summary>
    public void Hide(string name)
    {
        name = name.Trim();
        if (_settings is null || name.Length == 0)
        {
            return;
        }

        _settings.Update(s =>
        {
            foreach (var key in s.HiddenClientNames.Keys.Where(k => string.Equals(k, name, StringComparison.OrdinalIgnoreCase)).ToList())
            {
                s.HiddenClientNames.Remove(key);
            }

            s.HiddenClientNames[name] = DateTime.Now;
        });
        _log.Info("Clients", "A client name was hidden from suggestions");
    }

    public void Unhide(string name) =>
        _settings?.Update(s =>
        {
            foreach (var key in s.HiddenClientNames.Keys.Where(k => string.Equals(k, name, StringComparison.OrdinalIgnoreCase)).ToList())
            {
                s.HiddenClientNames.Remove(key);
            }
        });

    /// <summary>
    /// For AutoCompleteBox.AsyncPopulator: the box asks for names as the user types
    /// and fills its own list. The view-models used to replace a bound list from
    /// inside the client-name setter, which re-entered the box while it was still
    /// committing a picked suggestion and could leave the form with a different
    /// name than the box showed.
    /// </summary>
    public Task<IEnumerable<object>> PopulateAsync(string? text, CancellationToken cancellationToken) =>
        Task.FromResult<IEnumerable<object>>(Suggest(text));

    public async Task RefreshAsync()
    {
        try
        {
            await _index.RefreshAsync();
            _log.Debug("Clients", $"Suggestion index has {_index.Names.Count} name(s)");
        }
        catch (Exception error)
        {
            _log.Warning("Clients", "Client suggestions could not be refreshed", error);
        }
    }
}
