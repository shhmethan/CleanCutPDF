using Avalonia;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Markup.Xaml;
using Avalonia.Threading;
using CleanCutPDF.App.Services;
using CleanCutPDF.App.ViewModels;
using CleanCutPDF.App.Views;
using CleanCutPDF.Core;
using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.Export;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Licensing;
using CleanCutPDF.Core.Pdf;
using CleanCutPDF.Core.Services;
using CleanCutPDF.Core.Sessions;
using CleanCutPDF.Core.Updates;
using CleanCutPDF.Core.Workspaces;
using Microsoft.Extensions.DependencyInjection;

namespace CleanCutPDF.App;

public partial class App : Application
{
    private ServiceProvider? _services;
    private bool _cleanedUp;

    public override void Initialize() => AvaloniaXamlLoader.Load(this);

    public override void OnFrameworkInitializationCompleted()
    {
        _services = ConfigureServices();
        var log = _services.GetRequiredService<AppLog>();
        var paths = _services.GetRequiredService<AppPaths>();
        log.WriteSessionHeader(paths.DataDirectory);
        Avalonia.Logging.Logger.Sink = new AvaloniaLogBridge(log);
        HookGlobalErrorHandlers(_services.GetRequiredService<CrashLog>(), _services.GetRequiredService<ActivityService>());

        var settings = _services.GetRequiredService<ISettingsService>();
        settings.Changed += (_, current) => log.Verbose = current.VerboseLogging;

        if (ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
        {
            var startupFiles = (desktop.Args ?? []).Where(File.Exists).ToList();
            var window = new MainWindow(startupFiles)
            {
                DataContext = _services.GetRequiredService<MainWindowViewModel>()
            };
            _services.GetRequiredService<WindowDialogService>().Attach(window);
            desktop.MainWindow = window;

            // Save everything before the window goes away. The close is held
            // while saving runs asynchronously (never blocking the UI thread),
            // then repeated.
            window.Closing += async (_, e) =>
            {
                if (_cleanedUp)
                {
                    return;
                }

                e.Cancel = true;
                await CleanUpAsync();
                window.Close();
            };
            desktop.ShutdownRequested += async (_, e) =>
            {
                if (_cleanedUp)
                {
                    return;
                }

                e.Cancel = true; // OS sign-out or shutdown: same orderly save first.
                await CleanUpAsync();
                desktop.Shutdown();
            };
            desktop.Exit += (_, _) => _services?.Dispose();
        }

        base.OnFrameworkInitializationCompleted();
    }

    private static ServiceProvider ConfigureServices()
    {
        var services = new ServiceCollection();

        // Core
        // CLEANCUTPDF_DATA_DIR lets testers run against a throwaway data folder.
        services.AddSingleton(new AppPaths(Environment.GetEnvironmentVariable("CLEANCUTPDF_DATA_DIR")));
        services.AddSingleton(sp => new AppLog(sp.GetRequiredService<AppPaths>()));
        services.AddSingleton(sp => new CrashLog(sp.GetRequiredService<AppPaths>(), sp.GetRequiredService<AppLog>()));
        services.AddSingleton<ISettingsService, JsonSettingsService>();
        services.AddSingleton<LegacyDataLocator>();
        services.AddSingleton<IShellService, ShellService>();
        services.AddSingleton<IPdfEngine, PdfiumEngine>();
        services.AddSingleton<PagePreviewCache>();
        services.AddSingleton<PagePreviewService>();
        services.AddSingleton(sp => new WorkspaceStore(sp.GetRequiredService<AppPaths>(), sp.GetRequiredService<AppLog>()));
        services.AddSingleton<SessionStore>();
        services.AddSingleton<ExportHistory>();
        services.AddSingleton<ClientNameIndex>();
        services.AddSingleton<LegacyImporter>();
        services.AddSingleton(sp => new RenameService(sp.GetRequiredService<ExportHistory>(), sp.GetRequiredService<AppLog>()));
        services.AddSingleton(sp => new QuickSplitService(sp.GetRequiredService<IPdfEngine>(), sp.GetRequiredService<AppLog>()));
        services.AddSingleton(sp => new ExportService(sp.GetRequiredService<IPdfEngine>(),
            sp.GetRequiredService<ExportHistory>(), sp.GetRequiredService<AppLog>()));
        services.AddSingleton(_ =>
        {
            // Certificate validation stays on (1.x disabled it for the license check).
            var http = new HttpClient { Timeout = TimeSpan.FromSeconds(30) };
            http.DefaultRequestHeaders.UserAgent.ParseAdd($"CleanCutPDF/{AppInfo.Version.Split('-')[0]}");
            return http;
        });
        services.AddSingleton<LicenseService>(sp => new LicenseService(
            sp.GetRequiredService<HttpClient>(), sp.GetRequiredService<AppPaths>(), sp.GetRequiredService<CrashLog>()));
        services.AddSingleton<UpdateService>(sp => new UpdateService(
            sp.GetRequiredService<HttpClient>(), sp.GetRequiredService<ISettingsService>(),
            sp.GetRequiredService<AppPaths>(), sp.GetRequiredService<CrashLog>()));

        // App services
        services.AddSingleton<WindowDialogService>();
        services.AddSingleton<IDialogService>(sp => sp.GetRequiredService<WindowDialogService>());
        services.AddSingleton<ActivityService>();
        services.AddSingleton<ThemeService>();
        services.AddSingleton<DocumentStore>();
        services.AddSingleton<NavigationService>();
        services.AddSingleton<AppLifetimeService>();
        services.AddSingleton<ClientSuggestions>();

        // View-models (pages are long-lived so their state survives navigation)
        services.AddSingleton<MainWindowViewModel>();
        services.AddSingleton<InboxViewModel>();
        services.AddSingleton<SplitRenameViewModel>();
        services.AddSingleton<RenameOnlyViewModel>();
        services.AddSingleton<SettingsViewModel>();
        services.AddSingleton<LicenseViewModel>();
        services.AddSingleton<UpdatesViewModel>();
        services.AddSingleton<QuickSplitViewModel>();
        services.AddSingleton<WorkspacesViewModel>();
        services.AddSingleton<FolderShortcutsViewModel>();
        services.AddSingleton<LegacyImportViewModel>();

        return services.BuildServiceProvider();
    }

    private static void HookGlobalErrorHandlers(CrashLog crashLog, ActivityService activity)
    {
        AppDomain.CurrentDomain.UnhandledException += (_, e) =>
            crashLog.Write("Unhandled exception", e.ExceptionObject as Exception);

        TaskScheduler.UnobservedTaskException += (_, e) =>
        {
            crashLog.Write("Unobserved task exception", e.Exception);
            e.SetObserved();
        };

        // Keep the window open after a UI callback failure (same intent as the
        // Python app's report_callback_exception), but record the details.
        Dispatcher.UIThread.UnhandledException += (_, e) =>
        {
            crashLog.Write("UI thread exception", e.Exception);
            e.Handled = true;
            activity.Report("Something went wrong and was recorded in the diagnostic log. You can keep working.");
        };
    }

    private async Task CleanUpAsync()
    {
        if (_services is null || _cleanedUp)
        {
            return;
        }

        var log = _services.GetRequiredService<AppLog>();
        log.Info("Shutdown", "Closing CleanCutPDF");
        try
        {
            await _services.GetRequiredService<DocumentStore>().SaveNowAsync();
            await _services.GetRequiredService<ISettingsService>().FlushAsync();
        }
        catch (Exception error)
        {
            _services.GetRequiredService<CrashLog>().Write("Saving during shutdown failed", error);
        }

        await log.FlushAsync(TimeSpan.FromSeconds(2));
        _cleanedUp = true;
    }
}
