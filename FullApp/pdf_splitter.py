# ───── IMPORTS ─────
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from PyPDF2 import PdfReader, PdfWriter
from pathlib import Path
import re
import json
import sys
import datetime
from tkinterdnd2 import DND_FILES, TkinterDnD


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
GLOBAL_KEYBINDS_FILE = SETTINGS_FILE.parent / "keybinds.json"

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
class PDFSplitterApp(TkinterDnD.Tk):
    # ─── INITIALIZATION ───
    def __init__(self):
        super().__init__()
        self.title("CleanCutPDF Splitter")
        self.geometry("900x600")
        self.update_idletasks()
        self.state("zoomed")

        self.settings = {}
        self.load_settings()

        self.reader = None
        self.ranges = []
        self.entries = []
        self.last_exported_files = []

        legacy_theme = self.settings.get("theme", "")
        if legacy_theme in ["Light", "Dark"]:
            self.settings["theme"] = "Light Blue" if legacy_theme == "Light" else "Dark Blue"
            self.save_settings()

        self.theme = self.settings.get("theme", "Light Blue")
        theme_config = THEMES.get(self.theme, {"mode": "light", "theme": "blue"})
        ctk.set_appearance_mode(theme_config["mode"])
        ctk.set_default_color_theme(theme_config["theme"])

        self.font_size = self.settings.get("font_size", 12)

        self.notebook = ctk.CTkTabview(self)
        self.notebook.pack(fill="both", expand=True)
        self.after(100, self._apply_tab_font_size)

        self.splitter_tab = self.notebook.add("Splitter")
        self.settings_tab = self.notebook.add("Settings")
        self.log_tab = self.notebook.add("Logs")
        self.about_tab = self.notebook.add("About")
        self.keybinds_tab = self.notebook.add("Keybinds")

        self.build_splitter_tab()
        self.build_about_tab()
        self.build_settings_tab()
        self.build_log_tab()
        self.build_keybinds_tab()

        self._apply_font_size()
        self.apply_keybinds()

    # ─── Settings ───
    def load_settings(self):
        try:
            with open(SETTINGS_FILE, "r") as f:
                self.settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.settings = {}
        try:
            with open(GLOBAL_KEYBINDS_FILE, "r") as f:
                self.keybindings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.keybindings = {
                "Open PDF": "Control-o",
                "Export PDFs": "Control-e",
                "Reset": "Control-r",
                "Quit": "Control-q",
                "Search Logs": "Control-f",
                "Undo Last Export": "Control-z"
            }
            with open(GLOBAL_KEYBINDS_FILE, "w") as f:
                json.dump(self.keybindings, f, indent=2)
    def save_settings(self):
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(self.settings, f, indent=2)

    # ─── UI Tab Builder ───
    def build_splitter_tab(self):
        wrapper = ctk.CTkFrame(self.splitter_tab)
        wrapper.pack(pady=10, padx=10, fill="x")

        self.dnd_frame = tk.Frame(wrapper, bg="#2a2a2a", height=60)
        self.dnd_frame.pack(fill="x", pady=(5, 10))

        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.handle_drop)

        self.drop_label = ctk.CTkLabel(wrapper, text="📂 Drag and Drop a PDF Here")
        self.drop_label.pack()

        btn_container = ctk.CTkFrame(wrapper, fg_color="transparent")
        btn_container.pack(pady=5)

        self.btn_select_pdf = ctk.CTkButton(btn_container, text="Select PDF", command=self.load_pdf)
        self.btn_select_pdf.pack(side="left", padx=10)

        self.btn_refresh = ctk.CTkButton(btn_container, text="Refresh", command=self.reset_ui, state="disabled")
        self.btn_refresh.pack(side="left", padx=10)

        self.label_status = ctk.CTkLabel(self.splitter_tab, text="No PDF loaded")
        self.label_status.pack(pady=(5, 0))

        scroll_frame = ctk.CTkFrame(self.splitter_tab)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(scroll_frame, borderwidth=0, highlightthickness=0, bg="#2a2a2a")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.vsb = tk.Scrollbar(scroll_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)

        self.vsb.pack(side="right", fill="y")

        self.parts_frame = ctk.CTkFrame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.parts_frame, anchor="n")

        self.parts_frame.bind("<Configure>", self._check_scrollbar_visibility)
        self.canvas.bind("<Configure>", self._update_canvas_window_width)

        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self.canvas.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))

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
        self.theme_var.set(self.theme)

        ctk.CTkLabel(self.settings_tab, text="Default Export Folder").pack(pady=(20, 0))
        self.export_folder_var = ctk.StringVar(value=self.settings.get("export_folder", "Not Set"))
        export_frame = ctk.CTkFrame(self.settings_tab)
        export_frame.pack(pady=5, padx=20, fill="x")

        self.export_display = ctk.CTkEntry(export_frame, textvariable=self.export_folder_var, state="disabled")
        self.export_display.pack(side="left", fill="x", expand=True, padx=(0, 10))

        browse_button = ctk.CTkButton(export_frame, text="📁 Browse...", command=self.set_export_folder)
        browse_button.pack(side="left")

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
            "CleanCutPDF Splitter v1.2\n\n"
            "CleanCutPDF is a responsive, customizable tool for cleanly and efficiently splitting PDF documents.\n\n"
            "Current Features:\n"
            "• Drag-and-drop PDF support\n"
            "• Auto-detects split markers (e.g., 'SPLIT HERE')\n"
            "• Client name entry with responsive layout\n"
            "• Metadata-driven filename generation (Agency, Description, Date)\n"
            "• Auto-removal of blank pages (optional)\n"
            "• Custom export folder support\n"
            "• Scrollable, centered part blocks for clean organization\n"
            "• Export log with search, sorting, and read-only protection\n"
            "• Undo Last Export (Ctrl+Z), with deletion logging\n"
            "• Customizable keybindings (saved to keybinds.json)\n"
            "• Responsive font scaling and theme selection (Dark/Light)\n"
            "• Tab labels auto-resize with font setting\n"
            "• Keybinds tab supports scrollable layout and dynamic merging of missing keys\n\n"
            "Your settings and preferences are stored safely in your user directory.\n\n"
            "Designed by Ethan Brothers\n"
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
            bg="#1e1e1e",
            fg="white",
            insertbackground="white",
            borderwidth=0,
            highlightthickness=0
        )
        self.log_textbox.pack(fill="both", expand=True)
        self.log_textbox.config(state="disabled")

        # Define styles for coloring log lines
        self.log_textbox.tag_configure("date", foreground="#89CFF0")
        self.log_textbox.tag_configure("label", foreground="#AAAAAA")
        self.log_textbox.tag_configure("value", foreground="#FFFFFF")
        self.log_textbox.tag_configure("revoked", foreground="orange")
        self.log_textbox.tag_configure("skipped", foreground="red")

        self.load_full_log()
    def build_keybinds_tab(self):
        for widget in self.keybinds_tab.winfo_children():
            widget.destroy()

        wrapper = ctk.CTkFrame(self.keybinds_tab, fg_color="transparent")
        wrapper.pack(anchor="n", pady=20)

        ctk.CTkLabel(wrapper, text="Custom Keybindings").pack(pady=(10, 10))

        scroll_container = ctk.CTkFrame(wrapper, width=500, height=400, fg_color="transparent")
        scroll_container.pack()
        scroll_container.pack_propagate(False)

        scroll_frame = ctk.CTkScrollableFrame(scroll_container, width=500)
        scroll_frame.pack(fill="both", expand=True)
        scroll_frame._scrollbar.configure(width=0)

        self.keybind_vars = {}

        for action, combo in self.keybindings.items():
            row = ctk.CTkFrame(scroll_frame)
            row.pack(pady=5, anchor="center")

            ctk.CTkLabel(row, text=action, width=200, anchor="w").pack(side="left", padx=(0, 10))
            var = ctk.StringVar(value=combo)
            entry = ctk.CTkEntry(row, textvariable=var, width=200)
            entry.pack(side="left")
            self.keybind_vars[action] = var

        ctk.CTkButton(wrapper, text="Save Keybinds", command=self.save_keybinds).pack(pady=(20, 10))
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

        try:
            self.notebook.set(current_tab)
        except:
            pass
        self._check_scrollbar_visibility()

    # ─── UI Update Helpers ───
    def _apply_font_to_widget(self, widget, font):
        try:
            widget.configure(font=font)
        except:
            pass
        for child in widget.winfo_children():
            self._apply_font_to_widget(child, font)
    def _apply_font_size(self):
        font = ("Segoe UI", self.font_size)
        self.option_add("*Font", font)
        self.label_status.configure(font=font)
        self.export_display.configure(font=font)
        self.btn_process.configure(font=font)
        self.btn_refresh.configure(font=font)

        if self.client_name_entry:
            try:
                self.client_name_entry.configure(font=font)
            except tk.TclError:
                self.client_name_entry = None
        if hasattr(self, "btn_select_pdf"):
            self.btn_select_pdf.configure(font=font)
        if hasattr(self, "drop_label"):
            self.drop_label.configure(font=font)
        if hasattr(self, "client_name_label") and self.client_name_label is not None:
            try:
                if self.client_name_label.winfo_exists():
                    self.client_name_label.configure(font=font)
            except tk.TclError:
                self.client_name_label = None

        for child in self.settings_tab.winfo_children():
            self._apply_font_to_widget(child, font)
        for part in self.parts_frame.winfo_children():
            self._apply_font_to_widget(part, font)
        for child in self.keybinds_tab.winfo_children():
            self._apply_font_to_widget(child, font)
        self._apply_tab_font_size()
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
        self.label_status.configure(text="Ready")
        self.btn_process.configure(state="disabled")
        self.btn_refresh.configure(state="disabled")
        if self.client_name_entry and self.client_name_entry.winfo_exists():
            self.client_name_entry.destroy()
            self.client_name_entry = None

        if self.client_name_label and self.client_name_label.winfo_exists():
            self.client_name_label.destroy()
            self.client_name_label = None

        for widget in self.parts_frame.winfo_children():
            widget.destroy()

        self.client_name_visible = False
        self.client_name_label = None
    def _on_canvas_scroll(self, *args):
        self.canvas.yview(*args)
        self._check_scrollbar_visibility()
    def _check_scrollbar_visibility(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        needs_scroll = self.canvas.bbox("all")[3] > self.canvas.winfo_height()
        if needs_scroll:
            self.vsb.pack(side="right", fill="y")
        else:
            self.vsb.pack_forget()
    def _update_canvas_window_width(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    def _apply_tab_font_size(self):
        font = ("Segoe UI", self.font_size)
        for child in self.notebook._segmented_button._buttons_dict.values():
            child.configure(font=font)
    def add_tooltip(self, widget, text):
        tooltip = tk.Toplevel(widget)
        tooltip.withdraw()
        tooltip.overrideredirect(True)
        tooltip.config(bg="#333333")

        label = tk.Label(
            tooltip,
            text=text,
            background="#333333",
            foreground="white",
            padx=6,
            pady=3,
            font=("Segoe UI", 10),
            wraplength=200
        )
        label.pack()

        def on_enter(event):
            x = event.x_root + 10
            y = event.y_root + 10
            tooltip.geometry(f"+{x}+{y}")
            tooltip.deiconify()

        def on_leave(event):
            tooltip.withdraw()

        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)


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

        parsed = [extract_log_info(line) for line in self.full_log_lines]

        if query:
            parsed = [entry for entry in parsed if query in entry["raw"].lower()]

        reverse = sort_mode in ["Date ↓", "Z → A"]
        if "Date" in sort_mode:
            parsed.sort(key=lambda x: x["date"], reverse=reverse)
        else:
            parsed.sort(key=lambda x: x["client"], reverse=reverse)

        # 🔓 Enable the log box to modify it
        self.log_textbox.config(state="normal")
        self.log_textbox.delete("1.0", "end")

        for entry in parsed:
            line = entry["raw"]

            date_match = re.match(r"\[(.*?)\]", line)
            if date_match:
                timestamp = date_match.group(0) + " "
                self.log_textbox.insert("end", timestamp, "date")
                line_body = line[len(timestamp):]
            else:
                line_body = line

            fields = re.findall(r"(\b\w+):\s*(.*?)(?=\s*\||$)", line_body)
            for label, value in fields:
                self.log_textbox.insert("end", f"{label}:", "label")
                self.log_textbox.insert("end", f" {value}  ", "value")

                if label == "Revoked" and value.strip() == "True":
                    self.log_textbox.insert("end", "⚠️", "revoked")
                if label == "Skipped" and value.strip() != "None":
                    self.log_textbox.insert("end", "⚠️", "skipped")

            self.log_textbox.insert("end", "\n")

        self.log_textbox.see("end")  # Optional: scroll to bottom
        self.log_textbox.config(state="disabled")  # 🔒 Lock it again

    # ─── PDF Load & Split ───
    def load_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if path:
            self.load_pdf_from_path(path)
    def load_pdf_from_path(self, path):
        try:
            self.reader = PdfReader(path)
            self.pdf_path = Path(path)
            self.ranges = self.detect_split_ranges()

            self.label_status.configure(text=f"Loaded: {self.pdf_path.name} ({len(self.ranges)} part(s))")

            print("[DEBUG] client_name_visible =", self.client_name_visible)

            if not self.client_name_visible:
                print("[DEBUG] creating client_outer")
                client_outer = ctk.CTkFrame(self.parts_frame, width=700, height=40, fg_color="transparent")
                client_outer.pack(pady=(10, 0))
                client_outer.pack_propagate(False)

                print("[DEBUG] creating client_name_label")
                self.client_name_label = ctk.CTkLabel(client_outer, text="Client Name:")
                self.client_name_label.pack(side="left", padx=(10, 10))

                print("[DEBUG] creating client_name_entry")
                self.client_name_entry = ctk.CTkEntry(
                    client_outer,
                    textvariable=self.client_name_var,
                    placeholder_text="Enter Client Name"
                )
                self.client_name_entry.pack(side="left", fill="x", expand=True)

                print("[DEBUG] client_name_entry assigned:", self.client_name_entry)


                def debug_entry_geometry():
                    if self.client_name_entry and self.client_name_entry.winfo_exists():
                        print("[DEBUG] ENTRY IS MAPPED:", self.client_name_entry.winfo_ismapped())
                        print("[DEBUG] ENTRY SIZE:", self.client_name_entry.winfo_width(), self.client_name_entry.winfo_height())
                    else:
                        print("[DEBUG] Entry is None or destroyed")

                self.after(100, debug_entry_geometry)

                self.client_name_visible = True
                print("[DEBUG] client_name_visible =", self.client_name_visible)

            self.render_parts()
            self.canvas.yview_moveto(0)
            self.btn_process.configure(state="normal")
            self.btn_refresh.configure(state="normal")
            self._apply_font_size()
        except Exception as e:
            messagebox.showerror("Failed to Load PDF", f"An error occurred:\n{str(e)}")
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
            if not (self.client_name_entry and widget == self.client_name_entry.master):
                widget.destroy()

        self.entries.clear()

        for idx, r in enumerate(self.ranges, start=1):
            frame = ctk.CTkFrame(self.parts_frame, width=640, fg_color="transparent")
            frame.pack(pady=10, anchor="center")

            ctk.CTkLabel(frame, text=f"Part {idx} — Pages {r['start']+1} to {r['end']+1}") \
                .grid(row=0, column=0, columnspan=2, pady=(0, 5), sticky="ew")

            revoked_var = ctk.BooleanVar()
            agency_var = ctk.StringVar()
            desc_var = ctk.StringVar(value="POA")
            date_var = ctk.StringVar()

            ctk.CTkSwitch(frame, text="Revoked", variable=revoked_var).grid(row=1, column=0, sticky="w")
            info_row = ctk.CTkFrame(frame, fg_color="transparent")
            info_row.grid(row=2, column=0, columnspan=2, sticky="w", pady=(5, 0))

            ctk.CTkLabel(info_row, text="Agency Code:").pack(side="left")

            info_icon = ctk.CTkLabel(info_row, text=" ℹ️", cursor="question_arrow")
            info_icon.pack(side="left", padx=(5, 0))

            tooltip_text = "Agency Codes:\n• i = IRS\n• f = FTB\n• e = EDD\n• c = CDTFA\n• b = BOE"
            self.add_tooltip(info_icon, tooltip_text)

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

            agency_var.trace_add("write", self.make_autofill_handler("agency", agency_var, idx - 1))
            desc_var.trace_add("write", self.make_autofill_handler("description", desc_var, idx - 1))
            date_var.trace_add("write", self.make_autofill_handler("date", date_var, idx - 1))
            revoked_var.trace_add("write", self.make_autofill_handler("revoked", revoked_var, idx - 1))

        self._check_scrollbar_visibility()
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

        log_lines = []
        self.last_exported_files = []

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

            self.last_exported_files.append(file_path)

            log_lines.append(
                f"Client: {client_name} | File: {fname} | Pages: {r['start']+1}-{r['end']+1} | "
                f"Skipped: {skipped_pages if skipped_pages else 'None'} | "
                f"Agency: {agency} | Desc: {desc} | Date: {formatted_date} | Revoked: {entry['revoked'].get()}"
            )

        # Append to global log
        with open(GLOBAL_LOG_FILE, "a", encoding="utf-8") as f:
            for line in log_lines:
                f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {line}\n")

        self.last_exported_files.append(file_path)

        self.load_full_log()

        self.label_status.configure(text=f"Exported to: {out_dir}")
        self.reset_ui()
    def handle_drop(self, event):
        path = event.data.strip("{}")  # Remove braces around paths with spaces (Windows)
        if path.lower().endswith(".pdf"):
            self.load_pdf_from_path(path)
        else:
            messagebox.showerror("Invalid File", "Only PDF files are supported.")

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

        try:
            m = int(digits[:2])
            d = int(digits[2:4])
            y = int(digits[4:])
            if y <= 50:
                y += 2000
            else:
                y += 1900

            date_obj = datetime.date(y, m, d)
        except ValueError:
            raise ValueError("Invalid date: not a real calendar day")

        today = datetime.date.today()
        if date_obj > today:
            raise ValueError("Date cannot be in the future")

        return f"{m}-{d:02d}-{y}"
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

    # ─── Keybinds ───
    def focus_search(self):
        try:
            self.log_tab.focus_set()
            for child in self.log_tab.winfo_children():
                if isinstance(child, ctk.CTkEntry) and child.cget("placeholder_text") == "Search":
                    child.focus_set()
                    break
        except:
            pass
    def save_keybinds(self):
        self.keybindings = {action: var.get() for action, var in self.keybind_vars.items()}
        with open(GLOBAL_KEYBINDS_FILE, "w") as f:
            json.dump(self.keybindings, f, indent=2)
        self.apply_keybinds()
        messagebox.showinfo("Keybinds Updated", "New keybindings have been saved.")
    def apply_keybinds(self):
        for action, combo in self.keybindings.items():
            if action == "Open PDF":
                self.bind_all(f"<{combo}>", lambda e: self.load_pdf())
            elif action == "Export PDFs":
                self.bind_all(f"<{combo}>", lambda e: self.export_pdfs())
            elif action == "Reset":
                self.bind_all(f"<{combo}>", lambda e: self.reset_ui())
            elif action == "Quit":
                self.bind_all(f"<{combo}>", lambda e: self.quit())
            elif action == "Search Logs":
                self.bind_all(f"<{combo}>", lambda e: self.focus_search())
            elif action == "Undo Last Export":
                self.bind_all(f"<{combo}>", lambda e: self._debug_keybind("Undo Last Export", self.undo_last_export))
    def undo_last_export(self):
        print("[DEBUG] Undo keybind triggered")
        print("[DEBUG] Files pending undo:", self.last_exported_files)

        if not self.last_exported_files:
            messagebox.showinfo("Undo", "No export to undo.")
            return

        deleted = 0
        for path in self.last_exported_files:
            try:
                if path.exists():
                    path.unlink()
                    deleted += 1

                    if path.parent.exists() and not any(path.parent.iterdir()):
                        path.parent.rmdir()
            except Exception as e:
                messagebox.showwarning("Undo Failed", f"Could not delete: {path.name}\n{e}")

        if deleted > 0:
            with open(GLOBAL_LOG_FILE, "a", encoding="utf-8") as f:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for path in self.last_exported_files:
                    f.write(f"[{timestamp}] Undo: Deleted '{path.name}' from '{path.parent}'\n")

            self.last_exported_files = []
        else:
            with open(GLOBAL_LOG_FILE, "a", encoding="utf-8") as f:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] Undo attempted, but no files were deleted.\n")
        self.load_full_log()
    def _debug_keybind(self, action_name, callback):
        print(f"[DEBUG] Keybind triggered: {action_name}")
        callback()


if __name__ == "__main__":
    app = PDFSplitterApp()
    app.mainloop()