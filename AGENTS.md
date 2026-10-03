# CleanCutPDF: context for Codex

This repo holds **two apps**:

- **`FullApp/`**: the original CleanCutPDF **1.x** (Python, CustomTkinter, PyPDF2, PyMuPDF), v1.10.1.
  It is the **working production version and the functional reference**. Never modify, rename,
  delete, or overwrite it, its build/installer files, or the root `version.json` (that file feeds
  the 1.x updater, and its `download_url` points at the Python exe).
- **`CleanCutPDF.Avalonia/`**: the **2.x rewrite** in C# / .NET 10 / Avalonia 12, built in tested
  phases. All new work happens here.

Owner: Ethan (law/tax office workflow: scanning batches, splitting at SPLIT HERE sheets, naming
files from client/workspace fields).

## Ground rules from the user (always apply)

- Work directly in the files. Don't paste replacement code into chat, and don't zip.
- **Never commit, push, publish, or upload.** The user pushes. When a phase is done, tell them
  explicitly when it's safe to push and give a commit message. Their convention is
  `Working 2.0.0-alpha.N`. Give separate `git add CleanCutPDF.Avalonia`, `git commit`, and
  `git push origin master1` commands.
- Before each push: bump `<InformationalVersion>` in `CleanCutPDF.Avalonia/Directory.Build.props`
  **and** `CleanCutPDF.Avalonia/version.json` (`version`, plus a new changelog entry at the top of
  `changelog`, written as plain-language user-facing notes). The user asks for this every time.
- No destructive changes without approval. Explain before changing or removing files.
- Keep the solution building (0 warnings, 0 errors) and all tests passing after each step.
- Test for real: unit tests, and also run the app and drive it (see Testing). Report problems
  found and fixed honestly.
- Never touch the user's real data: `~/.cleancutpdf/` (1.x, read-only) or `~/.cleancutpdf-next/`
  (2.x) unless that is the point of the task. Use a throwaway data folder for tests.
- A copy of the app is often running from **Visual Studio**. Don't kill it, and build test copies
  to a scratch folder (see Building).

## Current status (latest pushed commit: `Working 2.0.0-alpha.4`)

Done and tested:

- **Phase 1**: solution and DI, navigation shell, background PDF engine (PDFium), page preview
  (cache, cancel, prefetch), settings, light/dark theme, crash log.
- **Licensing**: the saved license is checked locally at startup (no network); online recheck
  weekly in the background; 30-day offline grace; expiry enforced; revocation persists; only the
  key's SHA-256 hash is stored. The 1.x activation is carried over read-only. A lock screen
  appears over the window when the license doesn't allow use.
- **Updates**: background check **every launch** (user's choice), via
  `CleanCutPDF.Avalonia/version.json` on GitHub raw `master1`. Shows a non-blocking banner with a
  Download link only (no in-app install yet).
- **Diagnostic logging**: `AppLog` writes daily files in `logs/` (14 days kept). Debug entries
  are in memory unless "Detailed logging" is on. `crash.log` includes recent activity. Avalonia
  binding warnings are bridged into the log; transient "Value is null" ones go to Debug.
  Privacy: log file names and actions only, never client names or field values.
- **Phase 2 (Split & Rename)**:
  - SPLIT HERE detection (text, plus a visual fallback for image-only colored sheets), run in the
    background with progress.
  - Part cards with all 7 field types, autofill, Today/auto-today, currency formatting,
    conditional fields (Payment Method → Check Number), notes, and the Aa title-case button.
  - Export: validation, blank-page removal, Make Client Folder, `_2` unique names, 1.x-format
    export history, all-or-nothing on failure/cancel.
  - Inbox folders, bulk workspace changes, the batch workspace prompt, and session
    save/restore with cached detection.
- **Phase 3**:
  - Rename Only and Quick Split pages.
  - Workspaces & Fields editor: create/rename/delete workspaces, client label, summary, filename
    template with token buttons and live preview, field assignment and order, per-workspace
    default, notes, and the custom field library with every 1.x option.
  - Read-only import of 1.x data (Settings › Import), folder shortcuts, client-name suggestions.
- **Phase 4**:
  - Logs page: grouped by day and client, debounced background search, workspace/date filters,
    sort, export to CSV/TSV/TXT/PDF, Print (HTML), Clear Log to the Recycle Bin.
  - Undo Last Export, which moves files to the **Recycle Bin** (user's choice, not permanent
    delete).
  - Zoom window: fit width, Ctrl+scroll 50–500%.
  - SPLIT HERE sheet generator.
  - **Ctrl+Alt+D debug console**: live log viewer, the user's "admin" shortcut from 1.x.

- **Phase 5**:
  - Color themes: `AppSettings.Accent` (Blue/Green/Pink) on top of `Theme` (System/Light/Dark).
    `ThemeService` swaps one merged `ResourceDictionary` in `Application.Resources` (app brushes
    plus the Fluent `SystemAccentColor` ramp), live, with no rebuild.
  - Font family + size: `AppSettings.FontFamily` ("" = Inter) and `FontSize` (11–24, default 14).
    Resources `AppFontFamily`, `AppFontSize`, and `AppFontSizeSmall/Medium/Large/Header/Brand/
    Title/Icon`; no view has a hard-coded `FontSize` any more. Use those resources (or the
    `section-title` / `page-title` / `note` classes) in new XAML.
  - Keyboard shortcuts: `Core/Shortcuts/ShortcutCatalog` (12 actions, 1.x defaults, normalize,
    validate, clean). Only changes are stored, in `AppSettings.Keybinds` (action id → gesture,
    "" = turned off). `KeybindsViewModel` drives Settings (press-to-capture, conflicts, reset,
    Show Keybinds); `MainWindow` matches key presses and `MainWindowViewModel.RunShortcutAsync`
    runs them. Ctrl+Alt+D is fixed. Refused: keys without Ctrl/Alt (except F-keys) and
    Ctrl+A/C/V/X/Y/Z.
  - Reset Settings: `Core/Services/SettingsReset` (6-character code without 0/O/1/I). Copies
    `settings.json` and `workspaces.json` to `backups/reset-<timestamp>/`, then resets both live.
    Kept: keybinds, `LegacyImportedUtc`, `LastUpdateCheckUtc`, license, history, sessions, logs.
  - The 1.x importer also maps the accent, font family, font size (1.x 12 ↔ 2.x 14), and
    `keybinds.json`.

- **Phase 6 (built and tested as `2.0.0-alpha.5`; not pushed until the user says so)**:
  - Rule the user asked for: opening the designer and saving without changes must leave the
    form looking exactly like the default, and fields that were not moved must not change.
  - Model: `WorkspaceDefinition.Layout` (`Core/Workspaces/WorkspaceLayout.cs`), null = automatic
    stacked form. Tiles are field key → x/y/width/height on a surface that is always 720 wide and
    stands for the full width of a Part. Only body fields have tiles: header toggles
    (`IsHeaderField`) stay in the Part header (`WorkspaceCatalog.LayoutFieldKeys`). `Sync` runs in
    `Normalize` (every save) and in `Resolve`.
  - Designer: Workspaces › Form layout › Design Layout… (`LayoutDesignerWindow` +
    `LayoutDesignerViewModel`). It is drawn like one Part (header, mock fields). Drag to move,
    drag an edge or corner to resize, Snap to Grid, arrow keys move, Shift+arrows resize,
    Ctrl = 1 px, Back to Automatic. `Result()` is null when the tiles are the stacked default
    (`IsStackedFor`), so the workspace stays on Automatic. Use Automatic Layout… removes a layout.
  - Form: `PartViewModel.IsFreeform`; `Controls/FreeformPanel` places fields with
    `FreeformLayout.Arrange`, which treats the design as rows: a tile of the default height (72)
    gets its field's natural height, a taller tile adds the difference, empty bands keep their
    size, hidden conditional fields collapse. A stacked layout is positioned identically to the
    automatic `StackPanel` (`FreeformPanelTests`).
  - 1.x import: `custom_layout` (freeform `elements`, or the first build's `field_positions`
    grid) is converted by `FreeformLayout.FromLegacy`. A 1.x tile for a header field is dropped.

Tests: `tests/CleanCutPDF.Core.Tests` (197) + `tests/CleanCutPDF.App.Tests` (21), all passing.

### Remaining phases

- **Phase 7 (next, not started)**: tutorial, Help page, packaging (Windows installer, macOS
  bundle), in-app update install (manifest has `sha256` for this).

## Repository layout (2.x)

```
CleanCutPDF.Avalonia/
  CleanCutPDF.sln, Directory.Build.props (version), Directory.Packages.props (central NuGet versions),
  global.json, version.json (2.x update manifest), README.md, docs/FEATURE_INVENTORY.md
  src/CleanCutPDF.Core/          UI-free logic (no Avalonia references)
    AppInfo.cs                   version (from InformationalVersion), product name
    Diagnostics/AppLog.cs        background file logger, Recent(), EntryWritten event
    Infrastructure/              AppPaths (data dir; CLEANCUTPDF_DATA_DIR override), AtomicFile,
                                 CrashLog, RemoteEndpoints, RecycleBin (SHFileOperation / ~/.Trash)
    Models/                      AppSettings (+FolderShortcut), FileSignature, PageAnalysis, RenderedPage
    Pdf/                         PdfiumNative (P/Invoke), PdfWorkerThread, PdfiumRuntime (ONE shared
                                 PDF thread), PdfEngine (open/render/text/analyze/extract pages/
                                 create documents), PagePreviewCache/Service, SplitDetector,
                                 BlankPageDetector, PdfLayout (+SplitHereTemplate)
    Naming/                      DateFieldFormat, CurrencyFormat, NameCasing, AgencyCodes,
                                 FilenameBuilder (tokens, template, sanitize), PartValues, FieldRules
    Workspaces/                  FieldDefinition, WorkspaceCatalog (1.x defaults), WorkspaceStore
                                 (workspaces.json), WorkspaceEditing (add/rename/delete/merge…)
    Export/                      ExportService (+ExportValidator, ExportHistory), RenameAndQuickSplit
                                 (RenameService, QuickSplitService, ClientNameIndex)
    History/HistoryLog.cs        parse/filter/group/export history, ExportUndo
    Sessions/SessionStore.cs     sessions.json (documents, folders, values per workspace)
    Licensing/, Updates/         LicenseService, UpdateService, AppVersion
    Shortcuts/ShortcutCatalog.cs rebindable actions, 1.x defaults, gesture rules
    Services/                    SettingsService (JSON, debounced atomic saves), LegacyDataLocator,
                                 LegacyImporter (read-only 1.x import), ShellService, SettingsReset
  src/CleanCutPDF.App/           Avalonia 12 UI, MVVM (CommunityToolkit.Mvvm partial properties)
    App.axaml(.cs)               DI registrations, global field/Part DataTemplates, shutdown
                                 (window close is held while saves finish asynchronously)
    Services/                    DocumentStore (open PDFs, folders, detection queue, sessions),
                                 DialogService, ActivityService (status bar), ThemeService,
                                 NavigationService, ToolsService (zoom, template, undo, debug
                                 console), ClientSuggestions, AvaloniaLogBridge, AppLifetimeService
    ViewModels/ (+Editor/)       one VM per page; Editor/WorkspaceFormViewModel is shared by
                                 Split & Rename and Rename Only
    Views/, Controls/, Styles/AppStyles.axaml
  tests/CleanCutPDF.Core.Tests/  xUnit; RawPdf writes exact test PDFs; FakeHttpHandler, FakeClock,
                                 FakeRecycleBin
  tests/CleanCutPDF.App.Tests/   view-model tests (form, autofill, conditions)
```

User data for 2.x: `~/.cleancutpdf-next/`, containing `settings.json`, `workspaces.json`,
`sessions.json`, `export-history.log`, `license.json`, `update-cache.json`, `logs/`, and
`crash.log`.

## Key design decisions

- **PDFium directly** (bblanchon.PDFium.Win32/.macOS) for rendering, text, page analysis,
  splitting (`FPDF_ImportPagesByIndex` + `SaveAsCopy`), and creating PDFs (standard fonts).
  PDFtoImage was rejected because it needs SkiaSharp 4 and Avalonia 12 uses SkiaSharp 3.
  PDFium is not thread-safe, so **one process-wide worker thread** (`PdfiumRuntime`) with
  High/Low priority queues handles everything. Files are read into memory, so they are never
  locked.
- Everything slow is async and cancellable. Detection runs at Low priority so previews stay
  instant, and the document being viewed jumps the detection queue.
- Ported rules match 1.x exactly; this was verified by running the original Python functions
  (extracted with `ast`) side by side. **Intentional differences**:
  - The title-case "Mac" rule was dropped (1.x turned "Machado" into "MacHado").
  - Warnings appear inside the window instead of as popups.
  - If every page of a Part looks blank, all pages are kept.
  - Exports are all-or-nothing.
  - Quick Split asks for a folder when no export folder is set.
  - Rename Only writes history lines.
  - Undo and Clear Log use the Recycle Bin.
  - History export uses the current filters.
  - The filename editor is a text box with token buttons (1.x was drag-and-drop).
  - Custom layouts: 1.x mapped the used tile area onto the Part and scaled heights with the
    width, so tiles could paint over each other, and made header toggles into tiles. 2.x
    stretches only horizontally, sizes rows by their content, and keeps header toggles in
    the header. Imported 1.x layouts are re-fitted to the 720 surface (96 px rows become
    72 px, edges snapped when snap was on).
  - The 1.x debug console's developer stress tests were not carried over.
- Export-history line format is identical to 1.x `full.log` lines, so old and new history read the same.
- Booleans in part values are stored as `"true"`/`"false"` strings.

## Building and testing

- Build: `dotnet build CleanCutPDF.sln` (from `CleanCutPDF.Avalonia/`). Test: `dotnet test CleanCutPDF.sln`.
- If Visual Studio's running copy locks `bin/`, build the app to the scratch folder:
  `dotnet build src/CleanCutPDF.App -o <scratchpad>/appbuild`, then run `<scratchpad>/appbuild/CleanCutPDF.exe`.
- Run against a throwaway profile: set `CLEANCUTPDF_DATA_DIR=<scratch folder>`. Before testing
  exports, make sure that profile's `export_folder` is a scratch folder; the 1.x import sets it
  to the user's real `Downloads\Processed Client Files`.
- PDFs passed on the command line are imported into the Inbox (handy for tests).
- UI testing was done with PowerShell UI Automation scripts kept in the session scratchpad:
  `ui.ps1` (select list items, set text, invoke buttons, choose combo items), `shot.ps1`
  (screenshot one window), and `typepath.ps1` (type a path into a file dialog). File dialogs
  don't expose the file-name box via UIA, so type the path with the keyboard (Alt+N).
  - Accessible names: list items use the VM's `ToString()`, inputs use
    `AutomationProperties.Name`, and the zoom buttons are named "Zoom in" / "Zoom out".
  - Lists are virtualized, so off-screen rows can't be found until scrolled to.
  - Owned windows (dialogs, zoom, console) appear under the main window in the UIA tree.

## Environment gotchas (Windows, Git Bash + PowerShell 5.1)

- **Bash heredocs mangle escapes**: `\n` inside python/C# strings becomes a real newline, and
  apostrophes in comments can break parsing. Write edit scripts to files with the Write tool
  (scratchpad), then run them with `C:/Users/Ethan/IdeaProjects/CleanCutPDF/.venv/Scripts/python.exe <file>`.
- **PowerShell `Get-Content`/`Set-Content` corrupts UTF-8** (emoji/arrows became mojibake once).
  Don't edit source files through PowerShell; use the Write/Edit tools or Python with
  `encoding='utf-8'`.
- Some files are CRLF (`SettingsView.axaml`, `README.md`). Edit scripts should detect and
  preserve line endings.
- Python is in `.venv` at the repo root (it has PyMuPDF, PyPDF2, and Pillow, useful for checking
  parity with 1.x).

- **Fluent theme dictionaries**: Fluent's light brushes resolve resources under the `Default`
  theme key, not `Light`. A runtime `ThemeDictionaries` override keyed `Light` reaches the app's
  own brushes but not built-in controls (check boxes and selection stayed blue). Key the light
  dictionary `ThemeVariant.Default`.
- UI test helper: `ui.ps1` was rewritten in the Phase 5 session scratchpad (actions: windows,
  shot, nav, invoke, focus, combo, settext, keys, focused, names, select, rect, drag; `drag`
  moves the real mouse, and screen pixels are 1.25x app pixels on this display). `keys` refuses
  to send unless the test app is the foreground window: Windows will not bring it forward while
  the user is working in another window, and unguarded keys once went to the user's window.
  When that happens, test through view-models/panels in `App.Tests` and say so. UIA `Invoke` does not move
  keyboard focus, so call `focus` first when the next step sends keys. The `keys` action and
  any clipboard test overwrite the user's clipboard.

## Loose ends to mention or ask about

- Importing 1.x data into a test profile brings the user's real open PDFs (client files) into
  that profile's Inbox and sets its export folder to the real one. Don't open or export them.

- `CleanCutPDF.Avalonia/src/CleanCutPDF.Core/AppInfo.cs` has `ReferenceLegacyVersion = "2.0.0"`.
  It should probably be `"1.10.1"`, but it was changed outside the session, so it was left alone
  and flagged. The About text shows "modeled on v2.0.0".
- The user's 1.x Accounting filename template is `{client}{revoked}_{agency_description}` (no
  underscore after `{client}`). Flagged as possibly unintended, and not changed.
- Avalonia 12 API notes: `DragEventArgs.DataTransfer.TryGetFiles()`; clipboard
  `using Avalonia.Input.Platform` → `SetTextAsync` extension; `PlaceholderText` replaces the
  obsolete `Watermark`; Window `CanMinimize`/`CanMaximize` exist.
