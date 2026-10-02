using System.Text.Json;
using System.Text.Json.Serialization;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Models;

namespace CleanCutPDF.Core.Services;

public interface ISettingsService
{
    AppSettings Current { get; }

    /// <summary>Raised after settings are replaced or saved.</summary>
    event EventHandler<AppSettings>? Changed;

    Task LoadAsync(CancellationToken cancellationToken = default);

    /// <summary>Applies a change and persists it in the background (coalesced).</summary>
    void Update(Action<AppSettings> change);

    Task FlushAsync();
}

/// <summary>
/// JSON settings stored in the app's own data folder. Writes are atomic and
/// debounced so rapid toggles never block the UI or race each other.
/// </summary>
public sealed class JsonSettingsService(AppPaths paths, CrashLog crashLog) : ISettingsService
{
    internal static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        Converters = { new JsonStringEnumConverter(JsonNamingPolicy.SnakeCaseLower) }
    };

    private readonly SemaphoreSlim _saveLock = new(1, 1);
    private readonly object _gate = new();
    private AppSettings _current = new();
    private CancellationTokenSource? _pendingSave;
    private Task _lastSave = Task.CompletedTask;

    public AppSettings Current
    {
        get { lock (_gate) return _current; }
    }

    public event EventHandler<AppSettings>? Changed;

    public async Task LoadAsync(CancellationToken cancellationToken = default)
    {
        AppSettings loaded;
        try
        {
            if (File.Exists(paths.SettingsFile))
            {
                await using var stream = File.OpenRead(paths.SettingsFile);
                loaded = await JsonSerializer.DeserializeAsync<AppSettings>(stream, JsonOptions, cancellationToken)
                         ?? new AppSettings();
            }
            else
            {
                loaded = new AppSettings();
            }
        }
        catch (JsonException error)
        {
            // Keep the damaged file for inspection and continue with defaults.
            crashLog.Write("settings.json was unreadable; defaults used", error);
            TryBackupCorruptFile();
            loaded = new AppSettings();
        }

        lock (_gate)
        {
            _current = loaded;
        }

        Changed?.Invoke(this, loaded);
    }

    public void Update(Action<AppSettings> change)
    {
        AppSettings snapshot;
        CancellationTokenSource debounce;
        lock (_gate)
        {
            var next = _current.Clone();
            change(next);
            _current = next;
            snapshot = next;

            _pendingSave?.Cancel();
            debounce = _pendingSave = new CancellationTokenSource();
        }

        Changed?.Invoke(this, snapshot);
        _lastSave = SaveDebouncedAsync(debounce.Token);
    }

    public async Task FlushAsync()
    {
        lock (_gate)
        {
            _pendingSave?.Cancel();
            _pendingSave = null;
        }

        try
        {
            await _lastSave;
        }
        catch (OperationCanceledException)
        {
        }

        await SaveNowAsync(CancellationToken.None);
    }

    private async Task SaveDebouncedAsync(CancellationToken cancellationToken)
    {
        try
        {
            await Task.Delay(300, cancellationToken);
            await SaveNowAsync(cancellationToken);
        }
        catch (OperationCanceledException)
        {
        }
        catch (Exception error)
        {
            crashLog.Write("Saving settings failed", error);
        }
    }

    private async Task SaveNowAsync(CancellationToken cancellationToken)
    {
        await _saveLock.WaitAsync(cancellationToken);
        try
        {
            var json = JsonSerializer.Serialize(Current, JsonOptions);
            await AtomicFile.WriteAllTextAsync(paths.SettingsFile, json, cancellationToken);
        }
        finally
        {
            _saveLock.Release();
        }
    }

    private void TryBackupCorruptFile()
    {
        try
        {
            File.Copy(paths.SettingsFile, paths.SettingsFile + $".corrupt-{DateTime.Now:yyyyMMddHHmmss}", overwrite: false);
        }
        catch
        {
            // Best effort only.
        }
    }
}
