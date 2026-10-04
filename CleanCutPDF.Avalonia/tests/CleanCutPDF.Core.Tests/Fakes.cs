using System.Net;
using System.Text;

namespace CleanCutPDF.Core.Tests;

/// <summary>Returns a canned response per URL, or simulates a network failure.</summary>
internal sealed class FakeHttpHandler : HttpMessageHandler
{
    private readonly Dictionary<string, string> _responses = new();

    public bool Offline { get; set; }
    public int RequestCount { get; private set; }

    private readonly Dictionary<string, byte[]> _files = new();

    public void Respond(Uri url, string json) => _responses[url.AbsoluteUri] = json;

    /// <summary>A downloadable file (an installer).</summary>
    public void RespondFile(Uri url, byte[] content) => _files[url.AbsoluteUri] = content;

    protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
    {
        RequestCount++;
        if (Offline)
        {
            throw new HttpRequestException("No network (simulated)");
        }

        if (_files.TryGetValue(request.RequestUri!.AbsoluteUri, out var file))
        {
            return Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK) { Content = new ByteArrayContent(file) });
        }

        return Task.FromResult(_responses.TryGetValue(request.RequestUri!.AbsoluteUri, out var body)
            ? new HttpResponseMessage(HttpStatusCode.OK) { Content = new StringContent(body, Encoding.UTF8, "application/json") }
            : new HttpResponseMessage(HttpStatusCode.NotFound));
    }
}

internal sealed class FakeClock(DateTimeOffset start) : TimeProvider
{
    public DateTimeOffset Now { get; set; } = start;

    public override DateTimeOffset GetUtcNow() => Now;

    public override TimeZoneInfo LocalTimeZone => TimeZoneInfo.Utc;

    public void Advance(TimeSpan by) => Now += by;
}
