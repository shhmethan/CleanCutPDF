# CleanCutPDF 2 (C# / .NET 10 / Avalonia 12)

A ground-up rebuild of CleanCutPDF as a responsive, cross-platform (Windows +
macOS) desktop app. The Python application in `../FullApp` remains the working
version and the functional reference; nothing here modifies it or its data.

See [docs/FEATURE_INVENTORY.md](docs/FEATURE_INVENTORY.md) for the full list of
existing features, which phase each one lands in, and the causes of lag in 1.x.

## Build, test, run

```bash
dotnet build CleanCutPDF.sln
dotnet test CleanCutPDF.sln
dotnet run --project src/CleanCutPDF.App
```

PDF paths passed on the command line are imported into the Inbox at startup.

Requires the .NET 10 SDK. User data lives in `~/.cleancutpdf-next/`
(`settings.json`, `license.json`, `update-cache.json`, `crash.log`); set
`CLEANCUTPDF_DATA_DIR` to use a different folder for testing. The 1.x folder
`~/.cleancutpdf/` is only ever read.

## Licensing and updates

- **License:** read locally at startup (no network). The online list is rechecked at
  most once every 7 days, in the background. If the server cannot be reached, the app
  keeps working for 30 days after the last successful check. Expiry dates are enforced
  and revocations persist. Only the SHA-256 hash of the key is stored. An existing 1.x
  activation is carried over automatically (read-only).
- **Updates:** checked in the background every time the app opens (or with Check Now),
  using the separate manifest `CleanCutPDF.Avalonia/version.json`. That manifest only
  becomes reachable after it is pushed to `master1`; until then the check reports
  "not available" quietly. An available update shows a banner linking to the download
  page; nothing is installed automatically yet.

## Layout

```
CleanCutPDF.Avalonia/
├── CleanCutPDF.sln
├── Directory.Build.props       shared compiler settings and version
├── Directory.Packages.props    central NuGet versions
├── docs/FEATURE_INVENTORY.md
├── src/
│   ├── CleanCutPDF.Core/       UI-free business logic and PDF processing
│   │   ├── Infrastructure/     AppPaths, AtomicFile, CrashLog
│   │   ├── Models/             AppSettings, FileSignature, PdfDocumentInfo, RenderedPage
│   │   ├── Pdf/                PDFium bindings, worker thread, engine, preview cache/service
│   │   └── Services/           settings, legacy-data detection, open-folder shell
│   └── CleanCutPDF.App/        Avalonia UI (MVVM with CommunityToolkit.Mvvm)
│       ├── Services/           dialogs, activity/status bar, theme, navigation, document store
│       ├── ViewModels/
│       ├── Views/
│       └── Styles/
└── tests/CleanCutPDF.Core.Tests/   xUnit tests for Core
```

## Responsiveness design

| Problem in 1.x | Approach here |
|---|---|
| PDF work on the UI thread | All PDFium calls run on one dedicated background thread (`PdfWorkerThread`); the UI only awaits tasks |
| Preview re-opens the PDF per page | Document handles stay open (LRU of 6); the file is read once into memory, so it is never locked |
| Re-rendering pages already seen | `PagePreviewCache`: LRU of rendered pages bounded at 192 MB, keyed by file signature so edits invalidate it |
| Stale work piling up while paging quickly | Each new render cancels the previous one; cancelled queue items never start |
| Waiting for the next page | Neighbouring pages are prefetched at low priority; user requests always jump the queue |
| Blocking startup | Window shows first; settings and other startup work load asynchronously |
| Theme change rebuilds the UI | Theme variant swapped in place |
| License + version downloads block every launch | Saved license checked locally with a weekly background recheck; update check runs every launch in the background |

PDFium is process-global and not thread-safe, so the process shares exactly one
PDF thread (`PdfiumRuntime`).

## Libraries

| Package | Purpose | License |
|---|---|---|
| Avalonia 12, Avalonia.Desktop, Themes.Fluent, Fonts.Inter | UI | MIT |
| CommunityToolkit.Mvvm | MVVM source generators | MIT |
| Microsoft.Extensions.DependencyInjection | Composition | MIT |
| bblanchon.PDFium.Win32 / .macOS | Native PDFium: rendering and text extraction | Apache-2.0 / BSD |
| PDFsharp 6 | Writing split PDFs (Phase 2) | MIT |
| xUnit | Tests | Apache-2.0 |

PDFtoImage was considered but rejected: it requires SkiaSharp 4.x while
Avalonia 12 ships SkiaSharp 3.x.

## Phases

1. **Shell & architecture** (done): solution, DI, navigation (Inbox, Split & Rename,
   Rename Only, Settings), async import with drag and drop, background preview with
   cache/cancel/prefetch, settings persistence, theme switching, crash log, tests.
   Also done: **licensing** (local at startup; online recheck weekly in the background;
   30-day offline grace; carries over the 1.x activation) and **update checks** (every
   launch, in the background).
2. **Split & Rename core**: SPLIT HERE detection (text + visual fallback) in the
   background, part cards, workspace fields, autofill, Today/date/currency rules,
   filename builder, export with blank-page removal, export log, Inbox folders,
   bulk workspace changes, session save/restore.
3. **Rename Only, Quick Split, workspaces & custom fields editor**, read-only import
   of 1.x settings/sessions, folder shortcuts, client suggestions index.
4. **Logs** (virtualized, filtered off-thread, CSV/TSV/TXT/PDF export), undo last
   export, zoom window, SPLIT HERE template.
5. **Personalization**: color palettes, fonts, keybinds, settings reset.
6. **Workspace Layout Designer**.
7. **Tutorial, help, packaging** (Windows installer, macOS bundle) and installing updates in-app.
