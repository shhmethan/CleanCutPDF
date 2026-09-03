# CleanCutPDF

**CleanCutPDF** is a customizable Windows desktop app for splitting, naming, and exporting PDFs. It is designed for law firms, tax professionals, and anyone who regularly processes document batches and wants a faster, more organized workflow.

Built with Python and CustomTkinter, CleanCutPDF combines smart PDF splitting, reusable metadata fields, flexible workspaces, and export history in one app.

---

## ✨ Features

### 📄 Smart PDF Splitting

- Automatically detects `SPLIT HERE` pages and separates documents into parts
- Supports manual PDF selection and drag-and-drop
- Open multiple PDFs at once in separate tabs
- Includes **Quick Split** mode for processing batches of single-document files
- Optional automatic blank-page removal
- Optional warning when no split markers are detected

### 🏷️ Flexible Naming and Metadata

- Build filenames from client name and customizable metadata fields
- Create custom filename templates for each workspace
- Preserve intentional capitalization in filenames
- Use the **Aa** button beside Client Name to convert pasted names to title case
- Get client-name suggestions from previous export history
- Add a Today button to Date fields
- Set individual custom Date fields to automatically start with today’s date
- Receive a warning for missing or future dates without blocking export

### 🧩 Custom Fields and Workspaces

- Create reusable custom fields and assign them to any workspace
- Supported field types:
  - Text
  - Number
  - Currency
  - Date
  - Dropdown / Choice
  - Checkbox
  - Toggle
- Add default values, required fields, placeholders, field colors, and date formats
- Add conditional fields, such as showing Check Number only when Payment Method is `CK`
- Support an `Other` option in dropdowns with a free-text entry field
- Create, rename, and manage custom workspaces
- Customize each workspace’s client-field label, field order, notes, and filename template

### 🎨 Workspace Layout Designer

- Arrange workspace fields with drag-and-drop
- Resize field tiles
- Choose custom field colors
- Add workspace notes and reminders between fields
- Enable Snap to Grid and save the preference per workspace
- Click a Part heading to jump the PDF preview to that Part’s first page

### 📂 Folder Shortcuts and Exporting

- Set a default export folder
- Open the default output folder directly from the app
- Create custom folder shortcuts for frequently used locations
- Optionally create a client folder during export
- Prevent accidental overwrites by automatically creating unique filenames

### 🧾 Export Logs and History

- View export history inside the app
- Search and sort logs by date or client name
- Filter logs by workspace and export-date range
- Export filtered history to CSV, TSV, TXT, PDF, or Print
- Undo the most recent export when needed

### ⚙️ Personalization and Productivity

- Choose from Light, Dark, Blue, Green, and Pink themes
- Adjust font family and font size live
- Customize keyboard shortcuts in the app
- Automatically save and restore open PDFs and entered metadata
- Built-in tutorial for first-time users
- Built-in update checking and update installation support
- License activation with secure SHA-256 validation

---

## 💻 Installation

### 🟦 Windows (64-bit)

1. Go to the [Releases](https://github.com/shhmethan/CleanCutPDF/releases) page.
2. Download the latest installer, such as `CleanCutPDFv1.9.20.exe`.
3. Run the installer.
4. Follow the installation prompts.
5. Open CleanCutPDF and enter your license key on first launch.

Your existing settings, workspaces, custom fields, logs, and saved sessions are kept when you install a newer version.

---

## 🚀 Getting Started

1. Set your **Default Export Folder** in **Settings**.
2. Open a PDF in **Split & Rename** or drag one into the app.
3. Make sure your scanned batch uses `SPLIT HERE` pages where documents should separate.
4. Enter the client name and any needed metadata.
5. Review the PDF preview and filenames.
6. Click **Export PDFs**.

For a batch where every client has one document, use **Quick Split** instead.

---

## 🛠️ Built With

- [Python](https://www.python.org/)
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
- [PyPDF2](https://pypi.org/project/PyPDF2/)
- [PyMuPDF](https://pymupdf.readthedocs.io/)
- [Pillow](https://python-pillow.org/)
- [TkinterDnD2](https://pypi.org/project/tkinterdnd2/)

---

## 📌 Latest Version

**v1.9.20**

See the [Releases](https://github.com/shhmethan/CleanCutPDF/releases) page for the latest installer and full release notes.
