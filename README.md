# CleanCutPDF

**CleanCutPDF** is a Windows desktop app for splitting, naming, and exporting scanned PDFs. It is designed for law firms, tax professionals, and anyone who regularly processes document batches and wants a faster, more organized workflow.

Scan a stack of documents with a `SPLIT HERE` sheet between each one, and CleanCutPDF separates the scan into documents, names each file from what you type, and keeps a history of everything you export.

> **CleanCutPDF 2 is a preview release.** It is a complete rebuild of the original app (now C# and Avalonia instead of Python), made to stay fast and responsive with large batches. CleanCutPDF 1.x offers the upgrade from inside the app.

---

## ✨ Features

### 📄 Smart PDF Splitting

- Automatically detects `SPLIT HERE` pages and separates a scan into Parts
- Also finds colored separator sheets when the scanner produced no readable text
- Detection runs in the background, so you can page through the preview while it works
- **Inbox** for all your open PDFs, with folders, multi-select, and drag-and-drop
- **Quick Split** for batches with one document per client
- **Rename Only** for PDFs that are already separate documents
- Optional automatic blank-page removal
- Optional notice when no split markers are detected

### 🏷️ Flexible Naming and Metadata

- Build filenames from the client name and your own fields
- A filename format for each workspace, with a live preview
- Values carry down from one Part to the next until you change them
- Use the **Aa** button beside Client Name to convert pasted names to title case
- Client-name suggestions from your export folders and history
- Today button on Date fields, and Date fields that start with today's date
- A notice for missing or future dates without blocking the export

### 🧩 Custom Fields and Workspaces

- Create reusable fields and assign them to any workspace
- Field types: Text, Number, Currency, Date, Dropdown / Choice, Checkbox, Toggle
- Default values, required fields, placeholders, field colors, and date formats
- Conditional fields, such as showing Check Number only when Payment Method is `CK`
- An `Other` option in dropdowns with a free-text box
- Create, rename, and manage workspaces (Accounting and Legal are included)
- Set each workspace's client label, field order, notes, and filename format

### 🎨 Workspace Layout Designer

- Drag fields anywhere and resize them, for example two short fields side by side
- The designer shows the form as it really looks; fields you do not move stay as they are
- Snap to Grid, plus keyboard control for moving and resizing
- Return to the automatic layout at any time

### 📂 Folder Shortcuts and Exporting

- Set a default export folder and open it from the app
- Folder shortcuts for places you use often
- Optionally create a client folder during export
- Files are never overwritten: a unique name is used instead
- An export that fails or is cancelled keeps no files, so nothing is left half done

### 🧾 Export Logs and History

- Every exported or renamed file, grouped by day and client
- Search, filter by workspace and date range, and sort
- Export the history to CSV, TSV, TXT, or PDF, or print it
- **Undo Last Export** moves the most recent export to the Recycle Bin

### ⚙️ Personalization and Productivity

- Light or dark, in Blue, Green, or Pink, applied instantly
- Choose the font and text size; the whole app scales with it
- Keyboard shortcuts you can change, with the same defaults as 1.x
- Open PDFs and everything typed into them are restored when the app starts
- A tour on first start and a Help page with scanning and printing tips
- Updates install themselves: choose **Install Update** and the app updates and reopens
- License activation; only a SHA-256 hash of the key is stored

---

## 💻 Installation

### 🟦 Windows (64-bit)

1. Go to the [Releases](https://github.com/shhmethan/CleanCutPDF/releases) page.
2. Download the latest installer, such as `CleanCutPDF-2.0.0-alpha.6-Setup.exe`.
3. Run it. No administrator rights are needed.
4. Open CleanCutPDF and enter your license key on first launch.

The installer is not code-signed yet, so Windows may show a "Windows protected your PC" notice. Choose **More info**, then **Run anyway**.

After that you do not need to download anything again: when a new version is available, CleanCutPDF offers **Install Update**, checks the download against its published SHA-256, and updates itself.

### ⬆️ Upgrading from CleanCutPDF 1.x

- CleanCutPDF 1.x offers the upgrade itself once it has updated to 1.10.3. Accepting replaces 1.x with CleanCutPDF 2 in the same place, so your shortcuts keep working.
- Your 1.x settings, workspaces, custom fields, open PDFs, and export history are not changed. The first time CleanCutPDF 2 starts, it offers to bring them in, and you can also do this later from **Settings › Import**.
- An existing license is carried over.

---

## 🚀 Getting Started

1. Set your **Default Export Folder** in **Settings**.
2. Open a PDF from the **Inbox**, or drag one onto the window, then double-click it.
3. Make sure your scanned batch uses `SPLIT HERE` pages where documents should separate. You can save a printable sheet from the Inbox or the Help page.
4. Enter the client name and fill in the fields for each Part.
5. Review the PDF preview.
6. Click **Export PDFs**.

For a batch where every client has one document, use **Quick Split** instead. The **Help** page in the app explains each mode and has scanning tips.

---

## 🛠️ Built With

- [C# and .NET 10](https://dotnet.microsoft.com/)
- [Avalonia](https://avaloniaui.net/) for the interface
- [PDFium](https://pdfium.googlesource.com/pdfium/) for reading, previewing, and splitting PDFs
- [CommunityToolkit.Mvvm](https://learn.microsoft.com/dotnet/communitytoolkit/mvvm/)
- [NSIS](https://nsis.sourceforge.io/) for the installer

---

## 📁 In This Repository

- [`CleanCutPDF.Avalonia/`](CleanCutPDF.Avalonia) is CleanCutPDF 2. Its [README](CleanCutPDF.Avalonia/README.md) covers building, testing, and releasing.
- `FullApp/` is CleanCutPDF 1.x, the original Python app, kept for reference.

---

## 📌 Latest Version

**v2.0.0-alpha.6** (preview)

See the [Releases](https://github.com/shhmethan/CleanCutPDF/releases) page for the latest installer and full release notes. The last 1.x version is 1.10.3.
