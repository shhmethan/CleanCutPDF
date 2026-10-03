using System.Text.RegularExpressions;
using Avalonia.Logging;
using CleanCutPDF.Core.Diagnostics;

namespace CleanCutPDF.App.Services;

/// <summary>
/// Sends Avalonia's own warnings and errors (for example a broken data
/// binding that leaves a control blank) to the diagnostic log, so UI problems
/// that never throw an exception still leave a trace.
/// </summary>
public sealed partial class AvaloniaLogBridge(AppLog log) : ILogSink
{
    public bool IsEnabled(LogEventLevel level, string area) => level >= LogEventLevel.Warning;

    public void Log(LogEventLevel level, string area, object? source, string messageTemplate) =>
        Log(level, area, source, messageTemplate, []);

    public void Log(LogEventLevel level, string area, object? source, string messageTemplate,
        params object?[] propertyValues)
    {
        if (!IsEnabled(level, area))
        {
            return;
        }

        var index = 0;
        var message = Placeholder().Replace(messageTemplate,
            _ => index < propertyValues.Length ? propertyValues[index++]?.ToString() ?? "null" : "?");
        var where = source is null ? "" : $" ({source.GetType().Name})";

        // A binding that briefly sees null while a page or list row is being
        // attached or detached is normal; keep it for detailed logging only.
        var transient = area == LogArea.Binding && message.Contains("Value is null", StringComparison.Ordinal);
        var target = level >= LogEventLevel.Error ? LogLevel.Error : transient ? LogLevel.Debug : LogLevel.Warning;
        log.Write(target, $"UI/{area}", message + where);
    }

    [GeneratedRegex(@"\{[^{}]+\}")]
    private static partial Regex Placeholder();
}
