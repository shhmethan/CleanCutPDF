using Avalonia;
using Avalonia.Styling;
using Avalonia.Threading;
using CleanCutPDF.Core.Models;
using CleanCutPDF.Core.Services;

namespace CleanCutPDF.App.Services;

/// <summary>
/// Applies the theme by swapping the Avalonia theme variant in place. Unlike
/// the Python version, nothing is destroyed or rebuilt, so switching is instant.
/// </summary>
public sealed class ThemeService
{
    public ThemeService(ISettingsService settings)
    {
        settings.Changed += (_, current) => Apply(current.Theme);
    }

    public static void Apply(AppThemeMode mode)
    {
        void SetVariant()
        {
            if (Application.Current is null)
            {
                return;
            }

            Application.Current.RequestedThemeVariant = mode switch
            {
                AppThemeMode.Dark => ThemeVariant.Dark,
                AppThemeMode.Light => ThemeVariant.Light,
                _ => ThemeVariant.Default
            };
        }

        if (Dispatcher.UIThread.CheckAccess())
        {
            SetVariant();
        }
        else
        {
            Dispatcher.UIThread.Post(SetVariant);
        }
    }
}
