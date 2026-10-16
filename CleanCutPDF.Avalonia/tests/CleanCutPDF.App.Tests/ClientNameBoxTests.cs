using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.Primitives;
using Avalonia.Data;
using Avalonia.Headless;
using Avalonia.Input;
using Avalonia.Logging;
using Avalonia.Threading;
using Avalonia.VisualTree;
using CleanCutPDF.App.Services;
using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.Export;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Services;
using CommunityToolkit.Mvvm.ComponentModel;

namespace CleanCutPDF.App.Tests;

/// <summary>
/// The client-name box with its suggestions, driven with real key presses and
/// clicks. What the box shows must always be what the form holds: a picked
/// name that did not reach the form produced files without the client name.
/// </summary>
public sealed partial class ClientNameBoxTests : IDisposable
{
    private readonly string _folder = Path.Combine(Path.GetTempPath(), "cleancut-app-tests-" + Guid.NewGuid().ToString("N"));
    private readonly AppLog _log;
    private readonly ClientSuggestions _clients;

    public ClientNameBoxTests()
    {
        var paths = new AppPaths(_folder, Path.Combine(_folder, "legacy"));
        Directory.CreateDirectory(_folder);
        var history = new ExportHistory(paths);
        File.WriteAllLines(history.FilePath, new[] { "Smith", "Smith John", "Smith John Trust", "Asmar Inc", "Garcia Maria" }
            .Select(name => $"[2026-10-01 09:00:00] Workspace: Accounting | Client: {name} | File: a.pdf"));

        _log = new AppLog(paths);
        _clients = new ClientSuggestions(new ClientNameIndex(history), history, _log);
    }

    /// <summary>Stands in for the two pages: the same two bindings the client box has there.</summary>
    private sealed partial class Form(ClientSuggestions clients) : ObservableObject
    {
        [ObservableProperty]
        public partial string ClientName { get; set; } = "";

        public Func<string?, CancellationToken, Task<IEnumerable<object>>> ClientPopulator => clients.PopulateAsync;
    }

    private sealed class Warnings : ILogSink
    {
        public List<string> Lines { get; } = [];
        public bool IsEnabled(LogEventLevel level, string area) => level >= LogEventLevel.Warning;
        public void Log(LogEventLevel level, string area, object? source, string messageTemplate) => Lines.Add(messageTemplate);

        public void Log(LogEventLevel level, string area, object? source, string messageTemplate, params object?[] propertyValues) =>
            Lines.Add(messageTemplate + " " + string.Join(" ", propertyValues));
    }

    [Theory]
    [InlineData("click:0", "Smith")]
    [InlineData("click:1", "Smith John")]
    [InlineData("click:2", "Smith John Trust")]
    [InlineData("down enter", "Smith")]
    [InlineData("down down enter", "Smith John")]
    [InlineData("down down down enter", "Smith John Trust")]
    [InlineData("down down up enter", "Smith")]
    [InlineData("down down tab", "Smith John")]
    [InlineData("down click:2", "Smith John Trust")]
    [InlineData("down down click:0", "Smith")]
    [InlineData("type:i click:1", "Smith John")]
    [InlineData("down down enter type:x", "Smith Johnx")]
    [InlineData("down down enter back", "Smith Joh")]
    [InlineData("escape", "sm")]
    [InlineData("type:ith", "smith")]
    public async Task Picking_a_suggestion_always_reaches_the_form(string steps, string expected)
    {
        await _clients.RefreshAsync();
        await HeadlessApp.RunAsync(() =>
        {
            var previousSink = Logger.Sink;
            var warnings = new Warnings();
            Logger.Sink = warnings;
            var form = new Form(_clients);
            var box = ClientBox();
            var window = new Window
            {
                Width = 600, Height = 400, DataContext = form,
                Content = new StackPanel { Children = { box, new Button { Content = "Next control" } } }
            };
            window.Show();
            try
            {
                box.Focus();
                Dispatcher.UIThread.RunJobs();
                Type(window, "sm");
                Assert.True(box.IsDropDownOpen);
                // More than three now (1.x stopped at 3); names containing the text come after names starting with it.
                Assert.Equal(["Smith", "Smith John", "Smith John Trust", "Asmar Inc"], Items(box).Select(i => i.Content));

                foreach (var step in steps.Split(' '))
                {
                    switch (step.Split(':'))
                    {
                        case ["type", var text]: Type(window, text); break;
                        case ["click", var index]: Click(Items(box)[int.Parse(index)]); break;
                        case ["down"]: Press(window, PhysicalKey.ArrowDown); break;
                        case ["up"]: Press(window, PhysicalKey.ArrowUp); break;
                        case ["enter"]: Press(window, PhysicalKey.Enter); break;
                        case ["tab"]: Press(window, PhysicalKey.Tab); break;
                        case ["escape"]: Press(window, PhysicalKey.Escape); break;
                        case ["back"]: Press(window, PhysicalKey.Backspace); break;
                        default: throw new InvalidOperationException(step);
                    }
                }

                Assert.Equal(expected, box.Text);
                Assert.Equal(box.Text, form.ClientName);
                Assert.Empty(warnings.Lines);
            }
            finally
            {
                window.Close();
                Logger.Sink = previousSink;
            }
        });
    }

    [Fact]
    public async Task A_name_set_by_the_app_shows_in_the_box_without_opening_the_list()
    {
        await _clients.RefreshAsync();
        await HeadlessApp.RunAsync(() =>
        {
            var form = new Form(_clients);
            var box = ClientBox();
            var other = new Button { Content = "Elsewhere" };
            var window = new Window { Width = 600, Height = 400, DataContext = form, Content = new StackPanel { Children = { box, other } } };
            window.Show();
            try
            {
                other.Focus();
                form.ClientName = "Smith"; // Switching to another PDF.
                Dispatcher.UIThread.RunJobs();

                Assert.Equal("Smith", box.Text);
                Assert.False(box.IsDropDownOpen);
            }
            finally
            {
                window.Close();
            }
        });
    }

    /// <summary>Same settings as the box on Split &amp; Rename and Rename Only.</summary>
    private static AutoCompleteBox ClientBox() => new()
    {
        FilterMode = AutoCompleteFilterMode.None,
        MinimumPrefixLength = 1,
        MinimumPopulateDelay = TimeSpan.Zero,
        [!AutoCompleteBox.TextProperty] = new Binding(nameof(Form.ClientName)) { Mode = BindingMode.TwoWay },
        [!AutoCompleteBox.AsyncPopulatorProperty] = new Binding(nameof(Form.ClientPopulator))
    };

    private static List<ListBoxItem> Items(AutoCompleteBox box) =>
        box.GetVisualDescendants().OfType<Popup>().First().Child!.GetVisualDescendants().OfType<ListBoxItem>().ToList();

    private static void Type(Window window, string text)
    {
        foreach (var character in text)
        {
            window.KeyTextInput(character.ToString());
            Dispatcher.UIThread.RunJobs();
        }
    }

    private static void Press(Window window, PhysicalKey key)
    {
        window.KeyPressQwerty(key, RawInputModifiers.None);
        window.KeyReleaseQwerty(key, RawInputModifiers.None);
        Dispatcher.UIThread.RunJobs();
    }

    [Fact]
    public async Task A_hidden_name_is_left_out_until_it_is_shown_again()
    {
        var paths = new AppPaths(Path.Combine(_folder, "hide"), Path.Combine(_folder, "legacy"));
        Directory.CreateDirectory(paths.DataDirectory);
        var history = new ExportHistory(paths);
        File.Copy(new ExportHistory(new AppPaths(_folder, Path.Combine(_folder, "legacy"))).FilePath, history.FilePath);
        var settings = new JsonSettingsService(paths, new CrashLog(paths, _log));
        var clients = new ClientSuggestions(new ClientNameIndex(history), history, _log, settings);
        await clients.RefreshAsync();

        clients.Hide("smith john");

        Assert.Equal(["Smith", "Smith John Trust"], clients.Suggest("smith"));
        Assert.Equal(["smith john"], clients.HiddenNames);
        clients.Unhide("Smith John");
        Assert.Equal(["Smith", "Smith John", "Smith John Trust"], clients.Suggest("smith"));
        Assert.Empty(clients.HiddenNames);
        await settings.FlushAsync();
    }

    private static void Click(ListBoxItem item)
    {
        var root = TopLevel.GetTopLevel(item)!;
        var point = item.TranslatePoint(new Point(item.Bounds.Width / 2, item.Bounds.Height / 2), root)!.Value;
        root.MouseMove(point);
        root.MouseDown(point, MouseButton.Left);
        root.MouseUp(point, MouseButton.Left);
        Dispatcher.UIThread.RunJobs();
    }

    public void Dispose()
    {
        _log.Dispose();
        try
        {
            Directory.Delete(_folder, recursive: true);
        }
        catch (IOException)
        {
            // Best effort.
        }
    }
}
