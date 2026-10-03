using Avalonia.Controls;
using Avalonia.Controls.ApplicationLifetimes;
using CleanCutPDF.App.ViewModels;
using CleanCutPDF.App.Views;
using CleanCutPDF.Core.Diagnostics;
using CleanCutPDF.Core.History;
using CleanCutPDF.Core.Infrastructure;
using CleanCutPDF.Core.Pdf;
using CleanCutPDF.Core.Services;

namespace CleanCutPDF.App.Services;

/// <summary>Zoom window, SPLIT HERE template, and Undo Last Export (shared by several pages).</summary>
public sealed class ToolsService(
    IPdfEngine engine,
    DocumentStore documents,
    ExportUndo undo,
    IDialogService dialogs,
    IShellService shell,
    ActivityService activity,
    CrashLog crashLog,
    AppLog log)
{
    private DebugConsoleWindow? _console;

    /// <summary>Opens the debug console, or brings it to the front if it is already open.</summary>
    public void OpenDebugConsole()
    {
        if (_console is { } existing)
        {
            existing.Activate();
            return;
        }

        var window = new DebugConsoleWindow { DataContext = new DebugConsoleViewModel(log, shell) };
        window.Closed += (_, _) => _console = null;
        _console = window;
        log.Info("Console", "Debug console opened");
        var owner = (Avalonia.Application.Current?.ApplicationLifetime as IClassicDesktopStyleApplicationLifetime)?.MainWindow;
        if (owner is not null)
        {
            window.Show(owner);
        }
        else
        {
            window.Show();
        }
    }

    public void OpenZoom(IPreviewDocument document, int pageIndex)
    {
        var window = new ZoomWindow
        {
            DataContext = new ZoomViewModel(engine, log, document.FilePath, document.FileName,
                Math.Max(1, document.PageCount), pageIndex)
        };
        var owner = (Avalonia.Application.Current?.ApplicationLifetime as IClassicDesktopStyleApplicationLifetime)?.MainWindow;
        if (owner is not null)
        {
            window.Show(owner);
        }
        else
        {
            window.Show();
        }
    }

    public async Task SaveSplitHereTemplateAsync()
    {
        var path = await dialogs.SaveFileAsync("Save SPLIT HERE Sheet", "split_here_sheet.pdf", "pdf", "PDF files");
        if (path is null)
        {
            return;
        }

        try
        {
            var bytes = await engine.CreateDocumentAsync([SplitHereTemplate.Create()]);
            await File.WriteAllBytesAsync(path, bytes);
            log.Info("Tools", "Saved SPLIT HERE template");
            if (await dialogs.ConfirmAsync("SPLIT HERE Sheet",
                    $"Saved to:\n{path}\n\nPrint it on brightly colored paper and place a copy between documents.",
                    "Open It", "Close") && shell.OpenFile(path) is { } error)
            {
                await dialogs.ShowMessageAsync("Open File", error);
            }
        }
        catch (Exception error)
        {
            crashLog.Write("Saving the SPLIT HERE template failed", error);
            await dialogs.ShowMessageAsync("SPLIT HERE Sheet", $"The template could not be saved.\n\n{error.Message}");
        }
    }

    public bool CanUndo => documents.LastExportedFiles.Count > 0;

    /// <summary>Moves the most recent export's files to the Recycle Bin (after asking).</summary>
    public async Task UndoLastExportAsync()
    {
        var files = documents.LastExportedFiles;
        if (files.Count == 0)
        {
            await dialogs.ShowMessageAsync("Undo Last Export", "There is no export to undo.");
            return;
        }

        var names = string.Join("\n", files.Take(8).Select(Path.GetFileName)) + (files.Count > 8 ? "\n…" : "");
        if (!await dialogs.ConfirmAsync("Undo Last Export",
                $"Move the {files.Count} file(s) from the most recent export to the Recycle Bin?\n\n{names}\n\n" +
                "You can restore them from the Recycle Bin if needed.", "Move to Recycle Bin"))
        {
            return;
        }

        using var busy = activity.Begin("Undoing last export");
        var result = await undo.UndoAsync(files);
        documents.LastExportedFiles = [];
        if (result.Problems.Count > 0)
        {
            await dialogs.ShowMessageAsync("Undo Last Export",
                $"Moved {result.Recycled} file(s) to the Recycle Bin.\n\nSome files were not moved:\n" +
                string.Join("\n", result.Problems.Select(p => "• " + p)));
        }
        else
        {
            activity.Report($"Moved {result.Recycled} file(s) to the Recycle Bin");
        }
    }
}
