# ───── IMPORTS ─────
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PyPDF2 import PdfReader, PdfWriter
from pathlib import Path
import re
import json
import sys
import datetime


# ───── CONSTANTS & CONFIG ─────
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
    USER_DATA_DIR = Path.home() / ".cleancutpdf"
else:
    BASE_DIR = Path(__file__).parent
    USER_DATA_DIR = BASE_DIR

USER_DATA_DIR.mkdir(exist_ok=True)
SETTINGS_FILE = USER_DATA_DIR / "settings.json"
GLOBAL_LOG_FILE = SETTINGS_FILE.parent / "full.log"

ACRONYMS = {"POA", "LLC", "INC", "LP", "LLP", "PLC", "DBA", "CPA", "PC", "PLLC", "LLLP"}
THEMES = {
    "Light Blue": {"mode": "light", "theme": "blue"},
    "Dark Blue": {"mode": "dark", "theme": "blue"},
    "Dark Green": {"mode": "dark", "theme": "green"}
}
SORT_MODES = [
    "Date ↑", "Date ↓",
    "A → Z", "Z → A"
]

# ───── MAIN APPLICATION ─────
class PDFSplitterApp(ctk.CTk):
    # ─── INITIALIZATION ───
    def __init__(self):
        super().__init__()
        self.title("CleanCutPDF Splitter")
        self.geometry("900x600")
        self.settings = {}
        self.load_settings()

        self.reader = None
        self.ranges = []
        self.entries = []

        # Legacy theme handling
        legacy_theme = self.settings.get("theme", "")
        if legacy_theme in ["Light", "Dark"]:
            self.settings["theme"] = "Light Blue" if legacy_theme == "Light" else "Dark Blue"
            self.save_settings()

        # Apply theme
        self.theme = self.settings.get("theme", "Light Blue")
        theme_config = THEMES.get(self.theme, {"mode": "light", "theme": "blue"})
        ctk.set_appearance_mode(theme_config["mode"])
        ctk.set_default_color_theme(theme_config["theme"])

        self.font_size = self.settings.get("font_size", 12)

        self.notebook = ctk.CTkTabview(self)
        self.notebook.pack(fill="both", expand=True)

        self.splitter_tab = self.notebook.add("Splitter")
        self.settings_tab = self.notebook.add("Settings")
        self.log_tab = self.notebook.add("Logs")
        self.about_tab = self.notebook.add("About")

        self.build_splitter_tab()
        self.build_about_tab()
        self.build_settings_tab()
        self.build_log_tab()

        self._apply_font_size()

    # ─── SETTINGS ───
    def load_settings(self):
        try:
            with open(SETTINGS_FILE, "r") as f:
                self.settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.settings = {}
    def save_settings(self):
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(self.settings, f, indent=2)

    # ─── UI TAB BUILDER ───
    def build_splitter_tab(self):
        top_frame = ctk.CTkFrame(self.splitter_tab)
        top_frame.pack(pady=10)

        btn_container = ctk.CTkFrame(top_frame)
        btn_container.pack()

        ctk.CTkButton(btn_container, text="Select PDF", command=self.load_pdf).pack(side="left", padx=20)
        self.btn_refresh = ctk.CTkButton(btn_container, text="Refresh", command=self.reset_ui, state="disabled")
        self.btn_refresh.pack(side="left", padx=20)

        self.label_status = ctk.CTkLabel(self.splitter_tab, text="No PDF loaded")
        self.label_status.pack(pady=5)

        self.parts_frame = ctk.CTkFrame(self.splitter_tab)
        self.parts_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.client_name_var = ctk.StringVar()
        self.client_name_entry = None
        self.client_name_visible = False

        self.btn_process = ctk.CTkButton(self.splitter_tab, text="Export PDFs", command=self.export_pdfs, state="disabled")
        self.btn_process.pack(pady=10)
    def build_settings_tab(self):
        ctk.CTkLabel(self.settings_tab, text="Theme").pack(pady=(20, 0))
        self.theme_var = ctk.StringVar(value=self.theme)
        theme_menu = ctk.CTkOptionMenu(
            self.settings_tab,
            values=list(THEMES.keys()),
            variable=self.theme_var,
            command=self.change_theme
        )
        theme_menu.pack(pady=5)
        self.theme_var.set(self.theme)  # <- Set it after pack to update display

        ctk.CTkLabel(self.settings_tab, text="Default Export Folder").pack(pady=(20, 0))
        self.export_folder_var = ctk.StringVar(value=self.settings.get("export_folder", "Not Set"))
        export_frame = ctk.CTkFrame(self.settings_tab)
        export_frame.pack(pady=5, padx=20, fill="x")

        self.export_display = ctk.CTkEntry(export_frame, textvariable=self.export_folder_var, width=500, state="disabled")
        self.export_display.pack(side="left", padx=(0, 10), fill="x", expand=True)

        ctk.CTkButton(export_frame, text="📁 Browse...", command=self.set_export_folder).pack(side="left")

        ctk.CTkLabel(self.settings_tab, text="Font Size").pack(pady=(20, 0))
        self.font_size_var = ctk.IntVar(value=self.font_size)
        self.font_slider = ctk.CTkSlider(
            self.settings_tab, from_=12, to=22,
            variable=self.font_size_var, number_of_steps=10,
            command=self.update_font_size
        )
        self.font_slider.pack(pady=5)

        self.export_log_var = ctk.BooleanVar(value=self.settings.get("export_log_enabled", True))
        ctk.CTkCheckBox(
            self.settings_tab,
            text="Generate Export Log",
            variable=self.export_log_var,
            command=self.update_export_log_setting
        ).pack(pady=5)

        # Other toggles
        ctk.CTkLabel(self.settings_tab, text="Options").pack(pady=(20, 0))

        self.remove_blank_var = ctk.BooleanVar(value=self.settings.get("remove_blank_pages", True))
        remove_blank_checkbox = ctk.CTkCheckBox(
            self.settings_tab,
            text="Remove Blank Pages Automatically",
            variable=self.remove_blank_var,
            command=self.update_remove_blank_setting
        )
        remove_blank_checkbox.pack(pady=5)
    def build_about_tab(self):
        text = (
            "CleanCutPDF Splitter v1.0\n\n"
            "This tool helps you split and organize PDFs with minimal effort.\n\n"
            "Features:\n"
            "• Auto-detects split markers (e.g., 'SPLIT HERE')\n"
            "• Custom file naming with client info\n"
            "• Font size, theme, and export folder customization\n"
            "• Automatically removes blank pages (optional)\n"
            "• Searchable export log tab\n\n"
            "Developed by Ethan Brothers\n"
            "© 2025"
        )

        self.about_label = ctk.CTkLabel(
            self.about_tab,
            text=text,
            justify="center",
            anchor="center",
            wraplength=700,
            font=("Segoe UI", self.font_size)
        )
        self.about_label.pack(padx=20, pady=40, anchor="center")
    def build_log_tab(self):
        import tkinter as tk  # Ensure this is imported

        search_frame = ctk.CTkFrame(self.log_tab)
        search_frame.pack(fill="x", padx=10, pady=10)

        self.search_var = ctk.StringVar()
        self.sort_mode_var = ctk.StringVar(value="Date ↓")

        # Search bar
        ctk.CTkLabel(search_frame, text="Search:").pack(side="left", padx=(0, 5))
        search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True)
        search_entry.bind("<KeyRelease>", self.update_log_view)

        # Sort dropdown
        ctk.CTkLabel(search_frame, text="Sort:").pack(side="left", padx=(10, 5))
        sort_menu = ctk.CTkOptionMenu(
            search_frame,
            values=SORT_MODES,
            variable=self.sort_mode_var
        )
        sort_menu.pack(side="left")
        self.sort_mode_var.trace_add("write", self.update_log_view)

        # Log display (tk.Text inside a CTkFrame)
        log_text_frame = ctk.CTkFrame(self.log_tab)
        log_text_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.log_textbox = tk.Text(
            log_text_frame,
            wrap="word",
            bg="#1e1e1e",           # Match dark theme background
            fg="white",
            insertbackground="white",
            borderwidth=0,
            highlightthickness=0
        )
        self.log_textbox.pack(fill="both", expand=True)

        # Define styles for coloring log lines
        self.log_textbox.tag_configure("date", foreground="#89CFF0")      # Light blue
        self.log_textbox.tag_configure("label", foreground="#AAAAAA")     # Gray
        self.log_textbox.tag_configure("value", foreground="#FFFFFF")     # White
        self.log_textbox.tag_configure("revoked", foreground="orange")
        self.log_textbox.tag_configure("skipped", foreground="red")

        self.load_full_log()
    def rebuild_ui(self):
        # Save current tab name
        current_tab = self.notebook.get()

        # Destroy and rebuild notebook
        self.notebook.destroy()
        self.notebook = ctk.CTkTabview(self)
        self.notebook.pack(fill="both", expand=True)

        self.splitter_tab = self.notebook.add("Splitter")
        self.settings_tab = self.notebook.add("Settings")
        self.log_tab = self.notebook.add("Logs")
        self.about_tab = self.notebook.add("About")

        self.build_splitter_tab()
        self.build_settings_tab()
        self.build_log_tab()
        self.build_about_tab()

        self._apply_font_size()

        # ✅ Re-select the previous tab
        try:
            self.notebook.set(current_tab)
        except:
            pass  # Just in case the name doesn't match anymore

    # ─── UI UPDATE HELPERS ───
    def _apply_font_size(self):
        font = ("Segoe UI", self.font_size)
        self.option_add("*Font", font)
        self.label_status.configure(font=font)
        self.export_display.configure(font=font)
        self.btn_process.configure(font=font)
        self.btn_refresh.configure(font=font)

        # Only configure if the widget exists
        if self.client_name_entry:
            self.client_name_entry.configure(font=font)

        # Settings tab children
        for child in self.settings_tab.winfo_children():
            try:
                child.configure(font=font)
            except:
                pass

        # Part widgets
        for part in self.parts_frame.winfo_children():
            try:
                part.configure(font=font)
            except:
                pass
    def update_font_size(self, event=None):
        self.font_size = int(self.font_size_var.get())
        self.settings["font_size"] = self.font_size
        self.save_settings()
        self._apply_font_size()
    def change_theme(self, selected_name):
        theme_config = THEMES.get(selected_name)
        if theme_config:
            ctk.set_appearance_mode(theme_config["mode"])
            ctk.set_default_color_theme(theme_config["theme"])
            self.settings["theme"] = selected_name
            self.theme = selected_name  # ✅ update self.theme too
            self.save_settings()

            # Rebuild the UI to apply the new theme
            self.rebuild_ui()

            # ✅ After rebuilding, set the dropdown to the correct selection
            self.theme_var.set(selected_name)
    def reset_ui(self):
        self.reader = None
        self.ranges = []
        self.entries = []
        self.client_name_var.set("")
        self.label_status.configure(text="Ready")
        self.btn_process.configure(state="disabled")
        self.btn_refresh.configure(state="disabled")
        for widget in self.parts_frame.winfo_children():
            widget.destroy()
        self.client_name_visible = False

    # ─── Settings Toggles ───
    def update_remove_blank_setting(self):
        self.settings["remove_blank_pages"] = self.remove_blank_var.get()
        self.save_settings()
    def update_export_log_setting(self):
        self.settings["export_log_enabled"] = self.export_log_var.get()
        self.save_settings()
    def set_export_folder(self):
        folder = filedialog.askdirectory(title="Select Export Folder")
        if folder:
            prev = self.settings.get("export_folder")
            self.settings["export_folder"] = folder
            self.export_folder_var.set(folder)
            self.save_settings()

            if prev != folder:
                with open(GLOBAL_LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Export folder changed from '{prev}' to '{folder}'\n")

            self.load_full_log()

    # ─── Log Management ───
    def load_full_log(self):
        if GLOBAL_LOG_FILE.exists():
            with open(GLOBAL_LOG_FILE, "r") as f:
                self.full_log_lines = f.readlines()
        else:
            self.full_log_lines = []

        self.update_log_view()
    def update_log_view(self, *args):
        query = self.search_var.get().lower()
        sort_mode = self.sort_mode_var.get()

        def extract_log_info(line):
            info = {"raw": line, "client": "", "date": ""}
            client_match = re.search(r"Client:\s*(.*?)\s*\|", line)
            date_match = re.match(r"\[(.*?)\]", line)

            if client_match:
                info["client"] = client_match.group(1).strip().lower()
            if date_match:
                info["date"] = date_match.group(1)  # format: YYYY-MM-DD HH:MM:SS
            return info

        # Parse log lines
        parsed = [extract_log_info(line) for line in self.full_log_lines]

        # Filter by search query
        if query:
            parsed = [entry for entry in parsed if query in entry["raw"].lower()]

        # Sort based on dropdown selection
        reverse = sort_mode in ["Date ↓", "Z → A"]
        if "Date" in sort_mode:
            parsed.sort(key=lambda x: x["date"], reverse=reverse)
        else:
            parsed.sort(key=lambda x: x["client"], reverse=reverse)

        # Clear the textbox
        self.log_textbox.delete("1.0", "end")

        # Insert formatted, color-coded entries
        for entry in parsed:
            line = entry["raw"]

            # ─── Color the date ───
            date_match = re.match(r"\[(.*?)\]", line)
            if date_match:
                timestamp = date_match.group(0) + " "
                self.log_textbox.insert("end", timestamp, "date")
                line_body = line[len(timestamp):]
            else:
                line_body = line

            # ─── Color-coded fields ───
            fields = re.findall(r"(\b\w+):\s*(.*?)(?=\s*\||$)", line_body)
            for label, value in fields:
                self.log_textbox.insert("end", f"{label}:", "label")
                self.log_textbox.insert("end", f" {value}  ", "value")

                # Add alert emojis/tags
                if label == "Revoked" and value.strip() == "True":
                    self.log_textbox.insert("end", "⚠️", "revoked")
                if label == "Skipped" and value.strip() != "None":
                    self.log_textbox.insert("end", "⚠️", "skipped")

            self.log_textbox.insert("end", "\n")

    # ─── PDF Load & Split ───
    def load_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        self.reader = PdfReader(path)
        self.pdf_path = Path(path)
        self.ranges = self.detect_split_ranges()

        self.label_status.configure(text=f"Loaded: {self.pdf_path.name} ({len(self.ranges)} part(s))")

        if not self.client_name_visible:
            ctk.CTkLabel(self.parts_frame, text="Client Name:").pack(anchor="w", padx=10)
            self.client_name_entry = ctk.CTkEntry(
                self.parts_frame, textvariable=self.client_name_var, width=300,
                placeholder_text="Enter Client Name"
            )
            self.client_name_entry.pack(fill="x", padx=10, pady=5)
            self.client_name_visible = True

        self.render_parts()
        self.btn_process.configure(state="normal")
        self.btn_refresh.configure(state="normal")
    def detect_split_ranges(self):
        split_pages = []
        for idx, page in enumerate(self.reader.pages):
            text = page.extract_text() or ""
            words = [w for w in re.findall(r"\S+", text) if w.strip()]
            uppercase = [w.upper() for w in words]
            if any("SPLIT" in w for w in uppercase) and ("HERE" in uppercase or len(words) <= 3):
                split_pages.append(idx)

        ranges = []
        start = 0
        for sp in split_pages:
            end = sp - 1
            if start <= end:
                ranges.append({"start": start, "end": end})
            start = sp + 1

        if start < len(self.reader.pages):
            ranges.append({"start": start, "end": len(self.reader.pages) - 1})
        if not ranges:
            ranges = [{"start": 0, "end": len(self.reader.pages) - 1}]
        return ranges
    def render_parts(self):
        for widget in self.parts_frame.winfo_children():
            if widget not in (self.client_name_entry,):
                widget.destroy()

        self.entries.clear()

        for idx, r in enumerate(self.ranges, start=1):
            frame = ctk.CTkFrame(self.parts_frame)
            frame.pack(fill="x", padx=10, pady=10)

            ctk.CTkLabel(frame, text=f"Part {idx} — Pages {r['start']+1} to {r['end']+1}").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))

            revoked_var = ctk.BooleanVar()
            agency_var = ctk.StringVar()
            desc_var = ctk.StringVar(value="POA")
            date_var = ctk.StringVar()

            ctk.CTkSwitch(frame, text="Revoked", variable=revoked_var, onvalue=True, offvalue=False).grid(row=1, column=0, sticky="w")
            ctk.CTkLabel(frame, text="Agency Code:").grid(row=2, column=0, sticky="w")
            ctk.CTkEntry(frame, textvariable=agency_var).grid(row=2, column=1)

            ctk.CTkLabel(frame, text="Description:").grid(row=3, column=0, sticky="w")
            ctk.CTkEntry(frame, textvariable=desc_var).grid(row=3, column=1)

            ctk.CTkLabel(frame, text="Date (MMDDYY):").grid(row=4, column=0, sticky="w")
            ctk.CTkEntry(frame, textvariable=date_var).grid(row=4, column=1)

            self.entries.append({
                "range": r,
                "revoked": revoked_var,
                "agency": agency_var,
                "description": desc_var,
                "date": date_var
            })

            # Cascading autofill
            agency_var.trace_add("write", self.make_autofill_handler("agency", agency_var, idx - 1))
            desc_var.trace_add("write", self.make_autofill_handler("description", desc_var, idx - 1))
            date_var.trace_add("write", self.make_autofill_handler("date", date_var, idx - 1))
            revoked_var.trace_add("write", self.make_autofill_handler("revoked", revoked_var, idx - 1))
    def make_autofill_handler(self, field, var, i):
        def handler(*_):
            value = var.get()
            for j in range(i + 1, len(self.entries)):
                self.entries[j][field].set(value)
        return handler
    def export_pdfs(self):
        import datetime

        client_name = self.client_name_var.get().strip()
        if not client_name:
            messagebox.showerror("Missing Client Name", "Please enter a client name.")
            return

        folder = self.settings.get("export_folder")
        if not folder:
            folder = filedialog.askdirectory(title="Select Export Folder")
            if not folder:
                return

        out_dir = Path(folder) / client_name
        out_dir.mkdir(parents=True, exist_ok=True)

        log_lines = []

        for entry in self.entries:
            try:
                formatted_date = self.format_date(entry["date"].get())
            except ValueError:
                messagebox.showerror("Invalid Date", f"Invalid date: {entry['date'].get()}")
                return

            writer = PdfWriter()
            r = entry["range"]
            skipped_pages = []

            for p in range(r["start"], r["end"] + 1):
                page = self.reader.pages[p]
                if self.settings.get("remove_blank_pages", True) and self.is_blank_page(page):
                    skipped_pages.append(p + 1)
                    continue
                writer.add_page(page)

            parts = [client_name]
            if entry["revoked"].get():
                parts.append("Revoked")
            agency = self.get_agency(entry["agency"].get())
            desc = self.title_case(entry["description"].get())
            parts.append(f"{agency} {desc}" if agency else desc)
            parts.append(formatted_date)

            fname = "_".join(parts) + ".pdf"
            file_path = out_dir / fname

            with open(file_path, "wb") as f:
                writer.write(f)

            log_lines.append(
                f"Client: {client_name} | File: {fname} | Pages: {r['start']+1}-{r['end']+1} | "
                f"Skipped: {skipped_pages if skipped_pages else 'None'} | "
                f"Agency: {agency} | Desc: {desc} | Date: {formatted_date} | Revoked: {entry['revoked'].get()}"
            )

        # Append to global log
        with open(GLOBAL_LOG_FILE, "a", encoding="utf-8") as f:
            for line in log_lines:
                f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {line}\n")

        # Reload and refresh log tab
        self.load_full_log()

        self.label_status.configure(text=f"Exported to: {out_dir}")
        self.reset_ui()

    # ─── Text Utilities ───
    def is_blank_page(self, page):
        text = page.extract_text()
        if not text:
            return True
        stripped = "".join(text.split())
        return len(stripped) == 0
    def format_date(self, digits):
        if not re.fullmatch(r"\d{6}", digits):
            raise ValueError("Date must be 6 digits in MMDDYY format")
        m = int(digits[:2])
        d = digits[2:4]
        y = "20" + digits[4:]
        return f"{m}-{d}-{y}"
    def get_agency(self, code):
        return {
            "i": "IRS",
            "f": "FTB",
            "e": "EDD",
            "c": "CDTFA",
            "b": "BOE"
        }.get(code.strip().lower(), code.upper())
    def title_case(self, s):
        def _convert(word):
            clean = re.sub(r'[^A-Za-z]', '', word)
            up = clean.upper()
            if clean == "Inc" and word.endswith("."):
                return "Inc."
            if up in ACRONYMS and not word.endswith("."):
                return up
            if word.isupper():
                return word
            return word[:1].upper() + word[1:].lower()
        return " ".join(_convert(w) for w in s.split())

if __name__ == "__main__":
    app = PDFSplitterApp()
    app.mainloop()