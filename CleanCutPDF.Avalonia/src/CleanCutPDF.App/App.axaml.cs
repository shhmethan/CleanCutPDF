using Avalonia;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Markup.Xaml;
using Avalonia.Threading;
using CleanCutPDF.App.Services;
using CleanCutPDF.App.ViewModels;
using CleanCutPDF.App.Views;
using CleanCutPDF.Core;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Licensing;
using CleanCutPDF.Core.Pdf;
using CleanCutPDF.Core.Services;
using CleanCutPDF.Core.Updates;
using Microsoft.Extensions.DependencyInjection;

namespace CleanCutPDF.App;

public partial class App : Application
{
    private ServiceProvider? _services;

    public override void Initialize() => AvaloniaXamlLoader.Load(this);

    public override void OnFrameworkInitializationCompleted()
    {
        _services = ConfigureServices();
        HookGlobalErrorHandlers(_services.GetRequiredService<CrashLog>());

        if (ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
        {
            var startupFiles = (desktop.Args ?? []).Where(File.Exists).ToList();
            var window = new MainWindow(startupFiles)
            {
                DataContext = _services.GetRequiredService<MainWindowViewModel>()
            };
            _services.GetRequiredService<WindowDialogService>().Attach(window);
            desktop.MainWindow = window;
            desktop.ShutdownRequested += (_, _) => Shutdown();
        }

        base.OnFrameworkInitializationCompleted();
    }

    private static ServiceProvider ConfigureServices()
    {
        var services = new ServiceCollection();

        // Core
        // CLEANCUTPDF_DATA_DIR lets testers run against a throwaway data folder.
        services.AddSingleton(new AppPaths(Environment.GetEnvironmentVariable("CLEANCUTPDF_DATA_DIR")));
        services.AddSingleton<CrashLog>();
        services.AddSingleton<ISettingsService, JsonSettingsService>();
        services.AddSingleton<LegacyDataLocator>();
        services.AddSingleton<IShellService, ShellService>();
        services.AddSingleton<IPdfEngine, PdfiumEngine>();
        services.AddSingleton<PagePreviewCache>();
        services.AddSingleton<PagePreviewService>();
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

        // View-models (pages are long-lived so their state survives navigation)
        services.AddSingleton<MainWindowViewModel>();
        services.AddSingleton<InboxViewModel>();
        services.AddSingleton<SplitRenameViewModel>();
        services.AddSingleton<RenameOnlyViewModel>();
        services.AddSingleton<SettingsViewModel>();
        services.AddSingleton<LicenseViewModel>();
        services.AddSingleton<UpdatesViewModel>();

        return services.BuildServiceProvider();
    }

    private static void HookGlobalErrorHandlers(CrashLog crashLog)
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
        };
    }

    private void Shutdown()
    {
        if (_services is null)
        {
            return;
        }

        try
        {
            _services.GetRequiredService<ISettingsService>().FlushAsync().Wait(TimeSpan.FromSeconds(3));
        }
        catch (Exception error)
        {
            _services.GetRequiredService<CrashLog>().Write("Saving settings during shutdown failed", error);
        }

        _services.Dispose();
    }
}
