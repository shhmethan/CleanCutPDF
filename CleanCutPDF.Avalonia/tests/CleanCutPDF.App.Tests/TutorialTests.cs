using CleanCutPDF.App.Services;
using CleanCutPDF.App.ViewModels;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Services;

namespace CleanCutPDF.App.Tests;

public sealed class TutorialTests : IDisposable
{
    private readonly string _folder = Path.Combine(Path.GetTempPath(), "cleancut-app-tests-" + Guid.NewGuid().ToString("N"));
    private readonly JsonSettingsService _settings;
    private readonly NavigationService _navigation = new();
    private readonly List<AppPage> _visited = [];

    public TutorialTests()
    {
        var paths = new AppPaths(_folder, Path.Combine(_folder, "legacy"));
        _settings = new JsonSettingsService(paths, new CrashLog(paths));
        _navigation.NavigationRequested += (_, page) => _visited.Add(page);
    }

    [Fact]
    public void Tour_walks_through_every_page_and_is_then_marked_as_seen()
    {
        var tour = new TutorialViewModel(_navigation, _settings);
        var closed = 0;
        tour.CloseRequested += (_, _) => closed++;

        tour.Start();
        Assert.True(tour.IsFirst);
        Assert.Equal("Step 1 of 8", tour.Progress);
        Assert.Equal("Next", tour.NextText);
        Assert.False(_settings.Current.TutorialSeen);

        tour.BackCommand.Execute(null); // Nothing before the first step.
        Assert.Equal(0, tour.Index);

        while (!tour.IsLast)
        {
            tour.NextCommand.Execute(null);
        }

        Assert.Equal("Done", tour.NextText);
        Assert.Equal(0, closed);

        // Each step showed its own page; every page of the app is covered.
        Assert.Equal(tour.Steps.Select(s => s.Page), _visited);
        Assert.Equal(Enum.GetValues<AppPage>().Where(p => p != AppPage.Settings).Order(), _visited.Distinct().Order());

        tour.NextCommand.Execute(null); // Done
        Assert.Equal(1, closed);
        Assert.True(_settings.Current.TutorialSeen);
    }

    [Fact]
    public void Skipping_counts_as_seen_and_the_tour_restarts_from_the_top()
    {
        var tour = new TutorialViewModel(_navigation, _settings);
        tour.Start();
        tour.NextCommand.Execute(null);
        tour.NextCommand.Execute(null);
        tour.BackCommand.Execute(null);
        Assert.Equal(1, tour.Index);

        tour.FinishCommand.Execute(null); // Skip Tour, or closing the window.
        Assert.True(_settings.Current.TutorialSeen);

        tour.Start(); // Help › Show the Tour
        Assert.Equal(0, tour.Index);
        Assert.Equal(AppPage.Inbox, _visited[^1]);
    }

    [Fact]
    public void Reset_settings_does_not_bring_the_tour_or_the_import_offer_back()
    {
        _settings.Update(s =>
        {
            s.TutorialSeen = true;
            s.LegacyImportOffered = true;
        });

        var defaults = SettingsReset.Defaults(_settings.Current);
        Assert.True(defaults.TutorialSeen);
        Assert.True(defaults.LegacyImportOffered);
    }

    public void Dispose()
    {
        try
        {
            _settings.FlushAsync().GetAwaiter().GetResult();
            Directory.Delete(_folder, recursive: true);
        }
        catch (IOException)
        {
            // Left for the temp folder cleanup.
        }
    }
}
