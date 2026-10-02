using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Models;
using CleanCutPDF.Core.Services;

namespace CleanCutPDF.Core.Tests;

public sealed class SettingsServiceTests : IDisposable
{
    private readonly TempDirectory _temp = new();

    [Fact]
    public async Task Settings_round_trip_through_disk()
    {
        var paths = new AppPaths(_temp.Path);
        var service = new JsonSettingsService(paths, new CrashLog(paths));
        await service.LoadAsync();

        service.Update(s =>
        {
            s.Theme = AppThemeMode.Dark;
            s.ExportFolder = "C:/Exports";
        });
        await service.FlushAsync();

        var reloaded = new JsonSettingsService(paths, new CrashLog(paths));
        await reloaded.LoadAsync();
        Assert.Equal(AppThemeMode.Dark, reloaded.Current.Theme);
        Assert.Equal("C:/Exports", reloaded.Current.ExportFolder);
    }

    [Fact]
    public async Task Corrupt_settings_fall_back_to_defaults_and_are_backed_up()
    {
        var paths = new AppPaths(_temp.Path);
        paths.EnsureCreated();
        await File.WriteAllTextAsync(paths.SettingsFile, "{ not json");

        var service = new JsonSettingsService(paths, new CrashLog(paths));
        await service.LoadAsync();

        Assert.Equal(AppThemeMode.Light, service.Current.Theme);
        Assert.Single(Directory.GetFiles(_temp.Path, "settings.json.corrupt-*"));
    }

    [Fact]
    public void App_uses_separate_data_folder_from_python_app()
    {
        var paths = new AppPaths();
        Assert.NotEqual(
            Path.GetFullPath(paths.LegacyDataDirectory),
            Path.GetFullPath(paths.DataDirectory));
    }

    public void Dispose() => _temp.Dispose();
}
