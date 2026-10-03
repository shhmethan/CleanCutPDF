using Avalonia;
using Avalonia.Controls;
using Avalonia.Media;
using Avalonia.Styling;
using Avalonia.Threading;
using CleanCutPDF.Core.Models;
using CleanCutPDF.Core.Services;

namespace CleanCutPDF.App.Services;

/// <summary>
/// Applies light/dark, the accent palette, and the font by swapping one
/// resource dictionary in place. Unlike the Python version, nothing is
/// destroyed or rebuilt, so every change is instant.
/// </summary>
public sealed class ThemeService
{
    /// <summary>The 1.x font choices; the default (Inter) is offered separately.</summary>
    public static readonly IReadOnlyList<string> FontChoices =
        ["Segoe UI", "Arial", "Tahoma", "Verdana", "Consolas", "Courier New"];

    private static ResourceDictionary? _applied;
    private static (AppThemeMode, AppAccent, string, int)? _appliedKey;

    public ThemeService(ISettingsService settings)
    {
        settings.Changed += (_, current) => Apply(current);
    }

    /// <summary>Font choices that are installed on this computer.</summary>
    public static IReadOnlyList<string> InstalledFontChoices()
    {
        try
        {
            var installed = FontManager.Current.SystemFonts.Select(f => f.Name).ToHashSet(StringComparer.OrdinalIgnoreCase);
            return FontChoices.Where(installed.Contains).ToList();
        }
        catch
        {
            return FontChoices;
        }
    }

    public static void Apply(AppSettings settings)
    {
        var key = (settings.Theme, settings.Accent, settings.FontFamily, AppSettings.ClampFontSize(settings.FontSize));

        void ApplyNow()
        {
            if (Application.Current is not { } app || _appliedKey == key)
            {
                return;
            }

            var resources = Build(key.Accent, key.FontFamily, key.Item4);
            var merged = app.Resources.MergedDictionaries;
            merged.Add(resources);
            if (_applied is not null)
            {
                merged.Remove(_applied);
            }

            app.RequestedThemeVariant = key.Theme switch
            {
                AppThemeMode.Dark => ThemeVariant.Dark,
                AppThemeMode.Light => ThemeVariant.Light,
                _ => ThemeVariant.Default
            };
            _applied = resources;
            _appliedKey = key;
        }

        if (Dispatcher.UIThread.CheckAccess())
        {
            ApplyNow();
        }
        else
        {
            Dispatcher.UIThread.Post(ApplyNow);
        }
    }

    private static ResourceDictionary Build(AppAccent accent, string fontFamily, int fontSize)
    {
        var palette = Palette.For(accent);
        var resources = new ResourceDictionary();
        // Light goes under Default (which Light falls back to): Fluent's own
        // light brushes look their accent color up as Default, so a dictionary
        // keyed Light would leave check boxes and selection the stock blue.
        resources.ThemeDictionaries[ThemeVariant.Default] = palette.Light.ToResources();
        resources.ThemeDictionaries[ThemeVariant.Dark] = palette.Dark.ToResources();

        // Sizes derived from the base size so the whole UI scales together.
        double size = fontSize;
        resources["AppFontSize"] = size;
        resources["AppFontSizeSmall"] = Math.Max(9, size - 2);
        resources["AppFontSizeMedium"] = size + 1;
        resources["AppFontSizeLarge"] = size + 2;
        resources["AppFontSizeHeader"] = size + 4;
        resources["AppFontSizeBrand"] = size + 6;
        resources["AppFontSizeTitle"] = size + 8;
        resources["AppFontSizeIcon"] = size * 3;
        resources["ControlContentThemeFontSize"] = size; // Fluent text boxes, combo boxes, …

        if (!string.IsNullOrWhiteSpace(fontFamily))
        {
            var family = new FontFamily(fontFamily);
            resources["AppFontFamily"] = family;
            resources["ContentControlThemeFontFamily"] = family;
        }

        return resources;
    }

    /// <summary>App brushes plus the Fluent accent ramp for one accent in one variant.</summary>
    private sealed record Variant(string Accent, string AccentText, string Sidebar, string Card, string Border, string Preview)
    {
        public ResourceDictionary ToResources()
        {
            var accent = Color.Parse(Accent);
            return new ResourceDictionary
            {
                ["SidebarBackground"] = Brush(Sidebar),
                ["CardBackground"] = Brush(Card),
                ["CardBorder"] = Brush(Border),
                ["AccentText"] = Brush(AccentText),
                ["PreviewBackground"] = Brush(Preview),
                ["SystemAccentColor"] = accent,
                ["SystemAccentColorDark1"] = Mix(accent, Colors.Black, 0.15),
                ["SystemAccentColorDark2"] = Mix(accent, Colors.Black, 0.30),
                ["SystemAccentColorDark3"] = Mix(accent, Colors.Black, 0.45),
                ["SystemAccentColorLight1"] = Mix(accent, Colors.White, 0.15),
                ["SystemAccentColorLight2"] = Mix(accent, Colors.White, 0.30),
                ["SystemAccentColorLight3"] = Mix(accent, Colors.White, 0.45)
            };
        }

        private static SolidColorBrush Brush(string hex) => new(Color.Parse(hex));

        private static Color Mix(Color from, Color to, double amount) => Color.FromRgb(
            (byte)Math.Round(from.R + (to.R - from.R) * amount),
            (byte)Math.Round(from.G + (to.G - from.G) * amount),
            (byte)Math.Round(from.B + (to.B - from.B) * amount));
    }

    private sealed record Palette(Variant Light, Variant Dark)
    {
        public static Palette For(AppAccent accent) => accent switch
        {
            AppAccent.Green => new(
                new("#2E8B57", "#24754A", "#EDF4EF", "#FFFFFF", "#D3DFD7", "#E2E9E4"),
                new("#3FA36C", "#6FCF97", "#1E2621", "#283029", "#38443C", "#141A16")),
            AppAccent.Pink => new(
                new("#E75480", "#C2386A", "#FDF0F5", "#FFFFFF", "#F3C6D4", "#F1E3E8"),
                new("#E75480", "#FF8FB3", "#261E22", "#30272B", "#4A3840", "#1A1417")),
            _ => new(
                new("#2F7BBF", "#2F7BBF", "#EEF2F6", "#FFFFFF", "#D5DCE3", "#E3E7EB"),
                new("#3B8ED0", "#6CB2EB", "#1F242A", "#2A3036", "#3A424A", "#15191D"))
        };
    }
}
