using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using CleanCutPDF.Core.Infrastructure;

namespace CleanCutPDF.Core.Licensing;

public enum LicenseStatus
{
    /// <summary>Licensed and verified recently enough.</summary>
    Active,

    /// <summary>No license on this computer yet.</summary>
    Missing,

    /// <summary>The license list says this license has expired.</summary>
    Expired,

    /// <summary>The key is no longer in the license list.</summary>
    Revoked,

    /// <summary>Could not verify online for longer than the offline grace period.</summary>
    VerificationOverdue
}

public sealed record LicenseState(
    LicenseStatus Status,
    string? Company,
    DateOnly? Expires,
    DateTimeOffset? LastVerifiedUtc,
    bool OnlineCheckDue)
{
    public bool AllowsUse => Status == LicenseStatus.Active;
}

public enum LicenseCheckOutcome
{
    Verified,
    InvalidKey,
    Expired,
    Revoked,
    NetworkError
}

public sealed record LicenseCheckResult(LicenseCheckOutcome Outcome, LicenseState State, string Message);

/// <summary>
/// License activation and the weekly online recheck.
///
/// Policy: the license list is checked online at most once every
/// <see cref="RecheckInterval"/>, in the background. If the check cannot reach
/// the server the app keeps working, until <see cref="OfflineGracePeriod"/>
/// has passed since the last successful check. Only the SHA-256 hash of the
/// key is stored (the 1.x app stored the key itself).
/// </summary>
public sealed class LicenseService(HttpClient http, AppPaths paths, CrashLog crashLog, TimeProvider? clock = null)
{
    public static readonly TimeSpan RecheckInterval = TimeSpan.FromDays(7);
    public static readonly TimeSpan OfflineGracePeriod = TimeSpan.FromDays(30);

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower
    };

    private readonly TimeProvider _clock = clock ?? TimeProvider.System;
    private readonly SemaphoreSlim _gate = new(1, 1);
    private LicenseRecord? _record;

    public LicenseState Current { get; private set; } = new(LicenseStatus.Missing, null, null, null, false);

    /// <summary>
    /// Reads the saved license (or carries over a 1.x activation) without any
    /// network access, so startup is never delayed.
    /// </summary>
    public async Task<LicenseState> LoadAsync(CancellationToken cancellationToken = default)
    {
        await _gate.WaitAsync(cancellationToken);
        try
        {
            _record = await ReadRecordAsync(cancellationToken) ?? ImportLegacyRecord();
            if (_record is not null && !File.Exists(paths.LicenseFile))
            {
                await SaveRecordAsync(_record, cancellationToken);
            }

            return Current = Evaluate();
        }
        finally
        {
            _gate.Release();
        }
    }

    /// <summary>Checks the saved license against the online list.</summary>
    public async Task<LicenseCheckResult> VerifyOnlineAsync(CancellationToken cancellationToken = default)
    {
        await _gate.WaitAsync(cancellationToken);
        try
        {
            if (_record is null)
            {
                return new LicenseCheckResult(LicenseCheckOutcome.InvalidKey, Current = Evaluate(),
                    "No license is saved on this computer.");
            }

            var list = await TryFetchListAsync(cancellationToken);
            if (list is null)
            {
                return new LicenseCheckResult(LicenseCheckOutcome.NetworkError, Current = Evaluate(),
                    "The license server could not be reached. CleanCutPDF will try again later.");
            }

            if (!list.TryGetValue(_record.KeyHash, out var entry))
            {
                _record = _record with { Revoked = true };
                await SaveRecordAsync(_record, cancellationToken);
                return new LicenseCheckResult(LicenseCheckOutcome.Revoked, Current = Evaluate(),
                    "This license is no longer valid. Contact your administrator for a new key.");
            }

            _record = _record with
            {
                Revoked = false,
                Company = entry.Company ?? _record.Company,
                Expires = ParseDate(entry.Expires),
                LastVerifiedUtc = _clock.GetUtcNow()
            };
            await SaveRecordAsync(_record, cancellationToken);
            Current = Evaluate();
            return Current.Status == LicenseStatus.Expired
                ? new LicenseCheckResult(LicenseCheckOutcome.Expired, Current, ExpiredMessage(_record.Expires))
                : new LicenseCheckResult(LicenseCheckOutcome.Verified, Current, $"Licensed to {_record.Company}.");
        }
        finally
        {
            _gate.Release();
        }
    }

    /// <summary>Activates a newly entered key. Requires an internet connection.</summary>
    public async Task<LicenseCheckResult> ActivateAsync(string key, CancellationToken cancellationToken = default)
    {
        var trimmed = key.Trim();
        if (trimmed.Length == 0)
        {
            return new LicenseCheckResult(LicenseCheckOutcome.InvalidKey, Current, "Enter your license key.");
        }

        await _gate.WaitAsync(cancellationToken);
        try
        {
            var list = await TryFetchListAsync(cancellationToken);
            if (list is null)
            {
                return new LicenseCheckResult(LicenseCheckOutcome.NetworkError, Current,
                    "The license server could not be reached. Check your internet connection and try again.");
            }

            var hash = HashKey(trimmed);
            if (!list.TryGetValue(hash, out var entry))
            {
                return new LicenseCheckResult(LicenseCheckOutcome.InvalidKey, Current,
                    "That license key is not valid. Check it for typos and try again.");
            }

            var expires = ParseDate(entry.Expires);
            if (IsExpired(expires))
            {
                return new LicenseCheckResult(LicenseCheckOutcome.Expired, Current, ExpiredMessage(expires));
            }

            _record = new LicenseRecord(hash, entry.Company ?? "Unknown Organization", expires, _clock.GetUtcNow());
            await SaveRecordAsync(_record, cancellationToken);
            Current = Evaluate();
            return new LicenseCheckResult(LicenseCheckOutcome.Verified, Current, $"Licensed to {_record.Company}.");
        }
        finally
        {
            _gate.Release();
        }
    }

    /// <summary>Removes this app's saved license. The 1.x license file is not touched.</summary>
    public async Task RemoveAsync()
    {
        await _gate.WaitAsync();
        try
        {
            _record = null;
            if (File.Exists(paths.LicenseFile))
            {
                File.Delete(paths.LicenseFile);
            }

            // Remember the removal so the 1.x license is not silently re-imported.
            await AtomicFile.WriteAllTextAsync(paths.LicenseFile, "{\"removed\": true}");
            Current = Evaluate();
        }
        finally
        {
            _gate.Release();
        }
    }

    /// <summary>Same hashing as 1.x: SHA-256 of the UTF-8 key, lowercase hex.</summary>
    public static string HashKey(string key) =>
        Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(key.Trim())));

    private LicenseState Evaluate()
    {
        if (_record is null)
        {
            return new LicenseState(LicenseStatus.Missing, null, null, null, false);
        }

        var now = _clock.GetUtcNow();
        var sinceVerified = _record.LastVerifiedUtc is { } last ? now - last : TimeSpan.MaxValue;
        var status = _record.Revoked ? LicenseStatus.Revoked
            : IsExpired(_record.Expires) ? LicenseStatus.Expired
            : sinceVerified > OfflineGracePeriod ? LicenseStatus.VerificationOverdue
            : LicenseStatus.Active;

        return new LicenseState(status, _record.Company, _record.Expires, _record.LastVerifiedUtc,
            OnlineCheckDue: sinceVerified >= RecheckInterval);
    }

    private bool IsExpired(DateOnly? expires) =>
        expires is { } date && DateOnly.FromDateTime(_clock.GetLocalNow().DateTime) > date;

    private static string ExpiredMessage(DateOnly? expires) =>
        $"This license expired{(expires is { } d ? $" on {d:MMMM d, yyyy}" : "")}. Contact your administrator to renew it.";

    private async Task<Dictionary<string, LicenseListEntry>?> TryFetchListAsync(CancellationToken cancellationToken)
    {
        try
        {
            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            timeout.CancelAfter(RemoteEndpoints.RequestTimeout);
            await using var stream = await http.GetStreamAsync(RemoteEndpoints.LicenseList, timeout.Token);
            var document = await JsonSerializer.DeserializeAsync<LicenseListDocument>(stream, JsonOptions, timeout.Token);
            return document?.Licenses is { } licenses
                ? new Dictionary<string, LicenseListEntry>(licenses, StringComparer.OrdinalIgnoreCase)
                : null;
        }
        catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            return null; // Timed out.
        }
        catch (Exception error) when (error is HttpRequestException or IOException)
        {
            // Being offline or unable to reach the server is normal, not a crash.
            return null;
        }
        catch (JsonException error)
        {
            crashLog.Write("License list could not be fetched (invalid JSON)", error);
            return null;
        }
    }

    private async Task<LicenseRecord?> ReadRecordAsync(CancellationToken cancellationToken)
    {
        if (!File.Exists(paths.LicenseFile))
        {
            return null;
        }

        try
        {
            await using var stream = File.OpenRead(paths.LicenseFile);
            var record = await JsonSerializer.DeserializeAsync<LicenseRecord>(stream, JsonOptions, cancellationToken);
            return string.IsNullOrWhiteSpace(record?.KeyHash) ? null : record;
        }
        catch (JsonException error)
        {
            crashLog.Write("license.json was unreadable", error);
            return null;
        }
    }

    /// <summary>
    /// Carries over a 1.x activation so the user does not have to re-enter
    /// the key. 1.x rewrote its license file after every successful online
    /// check, so its timestamp is used as the last verification time.
    /// </summary>
    private LicenseRecord? ImportLegacyRecord()
    {
        if (File.Exists(paths.LicenseFile) || !File.Exists(paths.LegacyLicenseFile))
        {
            return null; // Either already set up here, or removed on purpose.
        }

        try
        {
            using var document = JsonDocument.Parse(File.ReadAllText(paths.LegacyLicenseFile));
            var root = document.RootElement;
            var key = root.TryGetProperty("license_key", out var k) ? k.GetString() : null;
            if (string.IsNullOrWhiteSpace(key))
            {
                return null;
            }

            var company = root.TryGetProperty("company", out var c) ? c.GetString() : null;
            var verified = new DateTimeOffset(File.GetLastWriteTimeUtc(paths.LegacyLicenseFile), TimeSpan.Zero);
            return new LicenseRecord(HashKey(key), company ?? "Unknown Organization", null, verified);
        }
        catch (Exception error) when (error is IOException or JsonException or UnauthorizedAccessException)
        {
            crashLog.Write("The 1.x license file could not be read", error);
            return null;
        }
    }

    private async Task SaveRecordAsync(LicenseRecord record, CancellationToken cancellationToken) =>
        await AtomicFile.WriteAllTextAsync(paths.LicenseFile, JsonSerializer.Serialize(record, JsonOptions), cancellationToken);

    private static DateOnly? ParseDate(string? value) =>
        DateOnly.TryParseExact(value, "yyyy-MM-dd", out var date) ? date : null;

    private sealed record LicenseRecord(
        string KeyHash, string Company, DateOnly? Expires, DateTimeOffset? LastVerifiedUtc, bool Revoked = false);

    private sealed class LicenseListDocument
    {
        public Dictionary<string, LicenseListEntry>? Licenses { get; set; }
    }

    private sealed class LicenseListEntry
    {
        public string? Company { get; set; }
        public string? Expires { get; set; }
    }
}
