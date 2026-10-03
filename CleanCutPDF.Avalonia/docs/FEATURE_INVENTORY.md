# CleanCutPDF Feature Inventory (Python v1.10.1 reference)

This inventory was produced by reading `FullApp/pdf_splitter.py` (10,288 lines),
`FullApp/update.py`, `README.md`, `FullApp/README.txt`, `version.json`, the
PyInstaller specs, the NSIS/Inno installer scripts, and the macOS GitHub
workflow. The Python application is the functional reference and is **not**
modified by the rewrite.

Legend for the "Plan" column:

- **Port** – behavior is recreated in C# (logic translated, not copied).
- **Redesign** – same user-facing result, different implementation (usually to fix lag).
- **Reuse** – existing asset/data file is reused as-is (read-only or copied).
- **Defer** – intentionally scheduled for a later phase.

---

## Status (2.0.0-alpha.1)

Done and tested: **Phase 1** (shell, background PDF engine, preview, settings, themes,
licensing, updates), **diagnostic logging**, **Phase 2** (Split & Rename core: detection,
fields, autofill, export, Inbox folders, sessions) and **Phase 3** (Rename Only, Quick
Split, workspace and field editors, 1.x import, folder shortcuts, client suggestions).

Rows below still say which phase each feature was planned for; everything listed for
Phases 1–3 is implemented. Remaining: Phase 4 (Logs page, undo last export, zoom window,
SPLIT HERE template), Phase 5 (color palettes, fonts, keybinds, settings reset),
Phase 6 (Workspace Layout Designer), Phase 7 (tutorial, help, packaging, in-app updates).

Deliberate differences from 1.x:
- Title case no longer turns "Machado" into "MacHado" (the automatic "Mac" rule was dropped).
- Warnings (no SPLIT HERE pages, future dates) appear in the window, with "Don't show again".
- If every page of a Part looks blank, all pages are kept instead of writing an empty PDF.
- Exports are all-or-nothing: a failed or cancelled export leaves no partial files.
- Quick Split asks for a folder when no export folder is set (1.x wrote next to the program).
- Rename Only records renamed files in the export history (so they appear in client suggestions).
- The visual drag-and-drop filename editor is a text box with field buttons and a live preview.

## 1. Project layout of the current application

| Item | Location | Notes |
|---|---|---|
| Entry point | `FullApp/pdf_splitter.py` → `PDFSplitterApp().mainloop()` | Single class, ~350 methods |
| Updater | `FullApp/update.py` (`CleanCutPDFUpdater.exe`) | Downloads installer, verifies SHA-256, relaunches app |
| Stress tests | `FullApp/stress_test.py` | Dev-only test harness launched from debug console |
| Resources | `FullApp/resources/favicon.ico`, `split_here_background.pdf` | Icon reused by the new app (copied) |
| Build | `CleanCutPDF.spec`, `CleanCutPDFUpdater.spec`, `pdf_splitter.spec` | PyInstaller one-file builds |
| Installers | `CleanCutPDFInstaller.nsi`, `CleanCutPDF-V1.iss`, `temp.iss` | NSIS / Inno Setup |
| CI | `.github/workflows/build-macos.yml` | PyInstaller macOS build |
| Release metadata | `version.json` (fetched from GitHub raw) | Version + per-version changelog |
| License list | `licenses.json` (fetched from GitHub raw) | SHA-256 key hash → company, expiry |

### Libraries
CustomTkinter + Tkinter (UI), TkinterDnD2 (drag & drop), PyPDF2 (page copy/write,
text fallback), PyMuPDF/fitz (text extraction, rendering, visual checks),
Pillow (image analysis/resizing), reportlab (optional log → PDF export).

### User data (`~/.cleancutpdf/`)
`settings.json`, `sessions.json`, `document_project.json` (Inbox folders),
`keybinds.json`, `full.log` (export history), `debug.log`, `crash.log`,
`last_action.json`, `license.json`, `pink_light.json`, `pink_dark.json`.

> The new app uses its own data folder (`~/.cleancutpdf-next/`) so it can never
> corrupt the working app's files. A read-only importer for the legacy folder is
> planned (Phase 3).

---

## 2. Feature inventory

### 2.1 Main shell
| Feature | Python behavior | Plan |
|---|---|---|
| Tabs | Split & Rename, Quick Split, Rename Only, Settings, Logs, About, Keybinds, Help | Port – left navigation; Phase 1 has Inbox / Split & Rename / Rename Only / Settings |
| Window title | `CleanCutPDF vX – Licensed to <company>` | Port |
| Start maximized | `state("zoomed")` | Port |
| Loading overlay | Full-screen overlay during startup / theme change | Redesign – non-blocking status bar + per-item progress |
| Crash diagnostics | `crash.log`, `last_action.json`, faulthandler, Tk callback hook | Port – global exception handlers write `crash.log` (Phase 1) |
| Debug console | Ctrl+Alt+D, live debug messages, dev stress tests | Defer (Phase 7) |
| Tutorial | Multi-step guided tour on first PDF load; rerun from Settings | Defer (Phase 7) |

### 2.2 Inbox / document explorer (Split & Rename sidebar)
| Feature | Python behavior | Plan |
|---|---|---|
| Document tree | Folders → PDFs, label `filename  [Workspace]` | Port (Phase 1 flat list, folders Phase 2) |
| Permanent Inbox folder | Cannot rename/delete; always first; landing view on startup | Port (Phase 2) |
| Custom folders | New / Rename / Delete (moves PDFs to Inbox) / Move Up / Move Down | Port (Phase 2) |
| Right-click context menu | Folder actions or document actions | Port (Phase 2) |
| Multi-select | Ctrl/Shift click; "N PDFs selected" status | Port (Phase 1 multi-select list) |
| Double-click to open | Prevents accidental editor loads | Port (Phase 1) |
| Change workspace for selected | Bulk workspace switch, updates labels in place | Port (Phase 2) |
| Move selected to folder | Virtual organization only; original files untouched | Port (Phase 2) |
| Close selected PDFs | Confirm dialog, clears stale preview | Port (Phase 1 basic, confirm in Phase 2) |
| Collapsible sidebar | "◀ Hide Inbox / ▶ Show Inbox" | Port (Phase 2) |
| Horizontal scrolling | Tree column sized to longest label + horizontal scrollbar | Port (Phase 1: list scrolls horizontally) |
| Max 3 rendered editors | Others shown as lightweight placeholder | Redesign – only the active editor is built; previews cached |

### 2.3 Opening PDFs
| Feature | Python behavior | Plan |
|---|---|---|
| Open PDFs dialog | Multi-select `.pdf` | Port (Phase 1) |
| Drag & drop | Whole window; paths with spaces handled | Port (Phase 1) |
| Batch workspace prompt | When >1 file: choose one workspace for all, saved as default | Port (Phase 2) |
| Duplicate guard | Same file stem already open → info message | Port (Phase 1, by full path) |
| No-split warning | Popup when no SPLIT HERE found in multi-page PDF, "don't show again" | Port (Phase 2, non-modal banner) |
| Session save / restore | `sessions.json` every 30 s + on close; lazy split detection with cached ranges validated by file size + mtime | Port (Phase 2) |

### 2.4 SPLIT HERE detection (core algorithm)
| Feature | Python behavior | Plan |
|---|---|---|
| Text marker | Page text contains `SPLITHERE` (letters only, upper) or both words `SPLIT` and `HERE` | Port (Phase 2) |
| Visual fallback | Only for pages with no text: colored, ≥82 % uniform background, ≤2.5 % dark pixels, one short wide centered dark text band | Port (Phase 2) |
| Ranges | Pages between markers; marker pages dropped; whole PDF as one part when none | Port (Phase 2) |
| Runs on UI thread | Yes – major source of lag | **Redesign** – background, cancellable, progress per page |

### 2.5 Split & Rename editor
| Feature | Python behavior | Plan |
|---|---|---|
| Header | Mode title, active filename, workspace selector, workspace summary | Port (Phase 2) |
| Optional client field | Workspace-specific label + "(optional)"; export allowed without it | Port (Phase 2) |
| Client suggestions | Top-3 matches from output-folder subfolders + `Client:` names in log; Tab/Enter/Up/Down | Port – **cached index** instead of reading the log on every keystroke (Phase 3) |
| Aa button | Force title case of pasted client name | Port (Phase 2) |
| Part cards | "Part N — Pages a to b"; clicking title jumps preview | Port (Phase 2) |
| Field rendering | Text, number, currency, date, choice (+Other free text), checkbox, toggle; header placement for toggles | Port (Phase 2) |
| Description autofill | Value typed in Part N propagates to later parts while they still hold the previously propagated value | Port (Phase 2) |
| Today button / auto-today | Date fields get a Today button; `auto_today` pre-fills blank dates | Port (Phase 2) |
| Currency normalization | On focus loss → `$1,234.56` | Port (Phase 2) |
| Conditional fields | e.g. Check Number visible only when Payment Method = CK | Port (Phase 2) |
| Field colors / tooltips / required `*` | Per field | Port (Phase 2/3) |
| Workspace notes | Notes at top, end, or directly under a field | Port (Phase 3) |
| Freeform layout | Workspace Designer tiles (x/y/w/h, snap to grid) | Defer (Phase 6) |
| Make Client Folder | Checkbox, default on | Port (Phase 2) |
| Reset Form / Show Keybinds | Buttons | Port (Phase 2/5) |
| Open Output Folder + folder shortcuts bar | Named, icon, color; manage dialog | Port (Phase 1: open export folder; shortcuts Phase 3) |

### 2.6 PDF preview
| Feature | Python behavior | Plan |
|---|---|---|
| Single preview per document | Re-opens PDF with fitz and rebuilds all widgets on every page change | **Redesign** – long-lived document handle on a dedicated PDF thread, LRU bitmap cache, cancellation of stale renders, next-page prefetch (Phase 1) |
| Prev / Next / page jump | Buttons hide at ends; "Page N of M"; validation | Port (Phase 1) |
| Zoom window | Maximized, Ctrl+wheel zoom 0.5–5×, fit-to-width | Port (Phase 4) |
| Stale preview after closing | Bug fixed in 1.10.1 | Redesign – preview bound to the selected document view-model |

### 2.7 Export
| Feature | Python behavior | Plan |
|---|---|---|
| Validation | Required fields, invalid date/currency (blocking), blank optional dates (confirm), future dates (warning, suppressible) | Port (Phase 2) |
| Output | `<export folder>[/<Client>]/<filename>.pdf`; asks for folder if unset | Port (Phase 2) |
| Unique names | `_2`, `_3`, … | Port (Phase 2) |
| Blank-page removal | Text ≥4 alphanumerics keeps page; annotations keep page; grayscale histogram ink thresholds | Port (Phase 2) |
| Export log line | `[ts] Workspace: … | Client: … | File: … | Pages: a-b | Skipped: … | Agency … | Fields: …` | Port (identical format for compatibility) |
| Close session after export | Yes | Port |
| Undo last export | Ctrl+Shift+Z, deletes files (and empty folder), logs it | Port (Phase 4, with confirmation) |
| Runs on UI thread | Yes | **Redesign** – background with progress & cancel |

### 2.8 Filename building
| Feature | Python behavior | Plan |
|---|---|---|
| Templates | `{client}_{revoked}_{agency_description}_{date}` style tokens per workspace | Port (Phase 2) |
| Special values | `revoked` → "Revoked"; checkbox/toggle → label when true; agency codes I/F/E/C/B → IRS/FTB/EDD/CDTFA/BOE; `\binv\b` → Invoice in Description; `agency_description` combined token; `check_number` gets leading space | Port (Phase 2) |
| Sanitizing | Illegal chars → `_`; collapse `\s+_`, `__`, double spaces; trim ` _-` and trailing `. `; Windows reserved names prefixed `_`; fallback "Document" | Port (Phase 2, unit tested) |
| Smart title case | Acronym list (POA, LLC, …), hyphenated words, Mc/Mac/O', preserves mixed case | Port (Phase 2, unit tested) |
| Date formats | M-D-YYYY, MM-DD-YYYY, YYYY.MM.DD, MMDDYY; flexible parsing of 7 input formats | Port (Phase 2, unit tested) |
| Visual filename editor | Free text + draggable field tokens, live preview | Port (Phase 3) |

### 2.9 Rename Only
| Feature | Python behavior | Plan |
|---|---|---|
| File list + editor | Add PDFs, list with ✕, Clear; each PDF is one part (no markers) | Port (Phase 3) |
| Action | "Create renamed copies" (to output folder) or "Rename originals in place" (confirm) | Port (Phase 3) |
| Uses workspace fields/template | Same filename pipeline as Split & Rename | Port (Phase 3) |

### 2.10 Quick Split
| Feature | Python behavior | Plan |
|---|---|---|
| Batch split | Split at markers, blank removal, `Quick Split Files/YYYY-MM-DD/` | Port (Phase 3) |
| Filename order | 4 options (original–part, part–original, original only, part only), `Part 01` padding | Port (Phase 3) |

### 2.11 Workspaces & custom fields (Settings)
| Feature | Python behavior | Plan |
|---|---|---|
| Built-in workspaces | Accounting (permanent), Legal | Port (Phase 3) |
| Create / rename / delete workspace | Accounting cannot be deleted | Port (Phase 3) |
| Client label, summary, filename template, field order, notes | Per workspace | Port (Phase 3) |
| Field library | Built-in: revoked, agency, description, date, matter_number, document_type, amount, payment_method, check_number (conditional), company | Port (Phase 3) |
| Field editor | Label, type, placeholder, default, color, required, autofill, title case, date format, auto-today, dropdown choices, conditional visibility | Port (Phase 3) |
| Assign / unassign / drag reorder | Per workspace | Port (Phase 3) |
| Workspace Layout Designer | Freeform tiles, resize, snap to grid | Defer (Phase 6) |
| Settings migrations | v1.8 `workspace_settings`, pre-workspace keys, old 3-column layouts, global auto-today | Port inside legacy importer (Phase 3) |

### 2.12 Logs / export history
| Feature | Python behavior | Plan |
|---|---|---|
| Grouped view | Date separators, bubble per (date, client) | Port – **virtualized list** (Phase 4) |
| Search + sort | Text search on every keystroke, sort by date/client | Redesign – debounced, background filtering (Phase 4) |
| Filters | Workspace (partial), export date from/to | Port (Phase 4) |
| Export | CSV, TSV, TXT, PDF, Print; filters for client/agency/export date/part date | Port (Phase 4) |
| Clear log | Confirm | Port (Phase 4) |
| Bounded log | Trim to 2,500 lines when >4 MB | Port (Phase 4) |

### 2.13 Appearance, keybinds, misc
| Feature | Python behavior | Plan |
|---|---|---|
| Themes | Light Blue, Dark Blue, Dark Green, Light Pink, Dark Pink (full UI rebuild) | Redesign – live resource swap, no rebuild (Phase 1 light/dark, palettes Phase 5) |
| Font family / size | Live | Port (Phase 5) |
| Keybinds | 8 rebindable actions (Open, Close Tab, Export, Reset, Quit, Search Logs, Undo Export, Paste Clipboard) | Port (Phase 5) |
| Reset settings | CAPTCHA-confirmed reset of settings.json only, then restart | Port (Phase 5) |
| SPLIT HERE template | Generates a one-page PDF | Port (Phase 4) |
| Help tab | Usage, Quick Split, printing tips | Port (Phase 7) |
| About / release notes | Version + changelog from remote `version.json` | **Done** – cached manifest, refreshed in background each launch |
| Update check | On startup (blocking 10 s timeout on UI thread) + manual; launches updater | **Done** – background check every launch + Check Now; banner instead of modal; in-app install Phase 7 |
| License | SHA-256 hash compared with remote list; cached locally; network fetch on every launch, unverified SSL | **Done** – local check at startup, weekly online recheck, 30-day offline grace, TLS verified, expiry enforced, hash-only storage |
| Export folder prompt on startup | If unset | Port (Phase 2) |

---

## 3. Identified causes of lag in the Python app

1. **Synchronous network calls during startup** – `check_license()` and
   `load_version_info()` both call `urlopen` on the UI thread before the
   window is usable (up to 10 s each when offline/slow).
2. **Split detection on the UI thread** – every page is text-extracted and
   scanned pages are rendered/analyzed pixel-by-pixel in Python loops.
3. **Preview re-opens the PDF on every page change** and destroys/rebuilds all
   preview widgets, rendering at 2× and then downscaling with LANCZOS.
4. **Export & blank-page removal on the UI thread** – rendering + histograms per page.
5. **Logs view rebuilds every widget on every keystroke** (no virtualization).
6. **Client suggestions read the entire log file on every keystroke.**
7. **Theme change destroys and rebuilds the entire UI.**
8. **Modal `wait_window` dialogs inside load loops** stall batch imports.

The new architecture addresses these with: a dedicated PDF worker thread with
long-lived document handles, async/await everywhere, `CancellationToken`s,
an LRU page cache, virtualized lists, cached indexes, and non-modal warnings.

---

## 4. Reuse vs. recreate

**Reused (read-only / copied):** application icon, release-notes data format
(`version.json`), export-log line format (so history stays compatible), legacy
user-data JSON formats (imported read-only), the business rules listed above.

**Recreated in C#:** all UI, PDF processing (PDFium for text/rendering,
PDFsharp for writing), split detection, blank detection, filename/date/currency
/title-case logic, settings & session persistence, logs, updater integration.

Python code cannot be called from the C# app; it is used purely as the
specification. Every ported rule gets a unit test in `CleanCutPDF.Core.Tests`.
