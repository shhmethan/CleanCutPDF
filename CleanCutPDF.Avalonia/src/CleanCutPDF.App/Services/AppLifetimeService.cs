using Avalonia;
using Avalonia.Controls.ApplicationLifetimes;

namespace CleanCutPDF.App.Services;

public sealed class AppLifetimeService
{
    public void Quit()
    {
        if (Application.Current?.ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
        {
            desktop.Shutdown();
        }
    }
}
