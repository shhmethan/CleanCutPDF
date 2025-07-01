import customtkinter as ctk
from tkinter import filedialog, messagebox
from PyPDF2 import PdfReader, PdfWriter
from pathlib import Path
import re
import json
import sys

if getattr(sys, 'frozen', False):
    # Running in PyInstaller bundle
    BASE_DIR = Path(sys._MEIPASS)
    USER_DATA_DIR = Path.home() / ".cleancutpdf"
else:
    BASE_DIR = Path(__file__).parent
    USER_DATA_DIR = BASE_DIR

USER_DATA_DIR.mkdir(exist_ok=True)
SETTINGS_FILE = Path.home() / ".cleancutpdf" / "settings.json"



ACRONYMS = {"POA", "LLC", "INC", "LP", "LLP", "PLC", "DBA", "CPA", "PC", "PLLC", "LLLP"}

THEMES = {
    "Light": "light",
    "Dark": "dark"
}


class PDFSplitterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CleanCutPDF Splitter")
        self.geometry("900x600")
        self.settings = {}
        self.load_settings()

        # Initialize missing settings with defaults
        updated = False
        if "font_size" not in self.settings:
            self.settings["font_size"] = 12
            updated = True
        if "theme" not in self.settings:
            self.settings["theme"] = "Light"
            updated = True
        if "export_folder" not in self.settings:
            self.settings["export_folder"] = ""
            updated = True
        if "reset_after_export" not in self.settings:
            self.settings["reset_after_export"] = True
            updated = True
        if "open_folder_after_export" not in self.settings:
            self.settings["open_folder_after_export"] = True
            updated = True
        if updated:
            self.save_settings()


        self.reader = None
        self.ranges = []
        self.entries = []

        self.theme = self.settings.get("theme", "Light")
        self.font_size = self.settings.get("font_size", 12)
        ctk.set_appearance_mode(THEMES.get(self.theme, "light"))
        ctk.set_default_color_theme("blue")

        self.notebook = ctk.CTkTabview(self)
        self.notebook.pack(fill="both", expand=True)

        self.splitter_tab = self.notebook.add("Splitter")
        self.settings_tab = self.notebook.add("Settings")

        self.build_splitter_tab()
        self.build_settings_tab()

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
        theme_menu = ctk.CTkOptionMenu(self.settings_tab, values=list(THEMES.keys()), variable=self.theme_var, command=self.change_theme)
        theme_menu.pack(pady=5)

        ctk.CTkLabel(self.settings_tab, text="Default Export Folder").pack(pady=(20, 0))
        self.export_folder_var = ctk.StringVar(value=self.settings.get("export_folder", "Not Set"))
        export_frame = ctk.CTkFrame(self.settings_tab)
        export_frame.pack(pady=5, padx=20, fill="x")

        self.export_display = ctk.CTkEntry(export_frame, textvariable=self.export_folder_var, width=500, state="disabled")
        self.export_display.pack(side="left", padx=(0, 10), fill="x", expand=True)

        ctk.CTkLabel(self.settings_tab, text="Font Size").pack(pady=(20, 0))
        self.font_size_var = ctk.IntVar(value=self.font_size)
        self.font_slider = ctk.CTkSlider(
            self.settings_tab, from_=8, to=20,
            variable=self.font_size_var, number_of_steps=12,
            command=self.update_font_size
        )
        self.font_slider.pack(pady=5)

        ctk.CTkButton(export_frame, text="📁 Browse...", command=self.set_export_folder).pack(side="left")

    def update_font_size(self, event=None):
        self.font_size = int(self.font_size_var.get())
        self.settings["font_size"] = self.font_size
        self.save_settings()
        self._apply_font_size()

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


    def change_theme(self, choice):
        self.settings["theme"] = choice
        self.save_settings()
        ctk.set_appearance_mode(THEMES.get(choice, "light"))

    def set_export_folder(self):
        folder = filedialog.askdirectory(title="Select Export Folder")
        if folder:
            self.settings["export_folder"] = folder
            self.export_folder_var.set(folder)
            self.save_settings()

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

        for entry in self.entries:
            try:
                formatted_date = self.format_date(entry["date"].get())
            except ValueError:
                messagebox.showerror("Invalid Date", f"Invalid date: {entry['date'].get()}")
                return

            writer = PdfWriter()
            r = entry["range"]
            for p in range(r["start"], r["end"] + 1):
                writer.add_page(self.reader.pages[p])

            parts = [client_name]
            if entry["revoked"].get():
                parts.append("Revoked")
            agency = self.get_agency(entry["agency"].get())
            desc = self.title_case(entry["description"].get())
            parts.append(f"{agency} {desc}" if agency else desc)
            parts.append(formatted_date)

            fname = "_".join(parts) + ".pdf"
            with open(out_dir / fname, "wb") as f:
                writer.write(f)

        self.label_status.configure(text=f"Exported to: {out_dir}")
        self.reset_ui()

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
