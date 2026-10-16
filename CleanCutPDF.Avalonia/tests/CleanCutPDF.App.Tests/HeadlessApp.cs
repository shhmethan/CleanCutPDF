using Avalonia;
using Avalonia.Headless;
using Avalonia.Themes.Fluent;

namespace CleanCutPDF.App.Tests;

/// <summary>
/// A windowless Avalonia application for tests that need real controls,
/// bindings, and keyboard input, with nothing shown on screen.
/// </summary>
public sealed class HeadlessApp : Application
{
    private static readonly Lazy<HeadlessUnitTestSession> Session =
        new(() => HeadlessUnitTestSession.StartNew(typeof(HeadlessApp)));

    public override void Initialize() => Styles.Add(new FluentTheme());

    public static AppBuilder BuildAvaloniaApp() =>
        AppBuilder.Configure<HeadlessApp>().UseHeadless(new AvaloniaHeadlessPlatformOptions());

    /// <summary>Runs a test body on the headless UI thread (one shared session for the test run).</summary>
    public static Task RunAsync(Action test) => Session.Value.Dispatch(test, CancellationToken.None);
}
