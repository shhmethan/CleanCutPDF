using Avalonia.Input;

namespace CleanCutPDF.App.Services;

/// <summary>Turns a key press into the stored shortcut text ("ctrl+shift+z").</summary>
public static class KeyGestureText
{
    /// <summary>Returns null while only modifier keys are held.</summary>
    public static string? From(KeyEventArgs e) => From(e.Key, e.KeyModifiers);

    public static string? From(Key key, KeyModifiers modifiers)
    {
        var name = key switch
        {
            Key.None or Key.LeftCtrl or Key.RightCtrl or Key.LeftShift or Key.RightShift or Key.LeftAlt
                or Key.RightAlt or Key.LWin or Key.RWin or Key.System or Key.DeadCharProcessed
                or Key.ImeProcessed => null,
            >= Key.A and <= Key.Z => key.ToString().ToLowerInvariant(),
            >= Key.D0 and <= Key.D9 => ((int)key - (int)Key.D0).ToString(),
            >= Key.NumPad0 and <= Key.NumPad9 => "num" + ((int)key - (int)Key.NumPad0),
            Key.Return => "enter",
            Key.Escape => "esc",
            Key.Back => "backspace",
            Key.OemPlus => "=",
            Key.OemMinus => "-",
            Key.OemComma => ",",
            Key.OemPeriod => ".",
            _ => key.ToString().ToLowerInvariant()
        };
        if (name is null)
        {
            return null;
        }

        var parts = new List<string>(4);
        if (modifiers.HasFlag(KeyModifiers.Control))
        {
            parts.Add("ctrl");
        }

        if (modifiers.HasFlag(KeyModifiers.Alt))
        {
            parts.Add("alt");
        }

        if (modifiers.HasFlag(KeyModifiers.Shift))
        {
            parts.Add("shift");
        }

        if (modifiers.HasFlag(KeyModifiers.Meta))
        {
            parts.Add("cmd");
        }

        parts.Add(name);
        return string.Join("+", parts);
    }
}
