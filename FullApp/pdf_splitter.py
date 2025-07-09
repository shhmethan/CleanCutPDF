# ───── IMPORTS ─────
import hashlib
import ssl
import urllib
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from PyPDF2 import PdfReader, PdfWriter
from pathlib import Path
import re
import io
import json
import sys
import datetime
from tkinterdnd2 import DND_FILES, TkinterDnD
import keyboard
import tkinter.scrolledtext as st

# ───── CONSTANTS & CONFIG ─────
BASE_DIR = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).parent
USER_DATA_DIR = Path.home() / ".cleancutpdf"

USER_DATA_DIR.mkdir(exist_ok=True)
SETTINGS_FILE = USER_DATA_DIR / "settings.json"
LOG_FILE = USER_DATA_DIR / "full.log"
KEYBINDS_FILE = USER_DATA_DIR / "keybinds.json"
PINK_LIGHT = USER_DATA_DIR / "pink_light.json"
PINK_DARK = USER_DATA_DIR / "pink_dark.json"
SESSION_FILE = USER_DATA_DIR / "sessions.json"
LICENSE_FILE = USER_DATA_DIR / "license.json"

ACRONYMS = {"POA", "LLC", "INC", "LP", "LLP", "PLC", "DBA", "CPA", "PC", "PLLC", "LLLP"}
THEMES = {
    "Light Blue": {"mode": "light", "theme": "blue"},
    "Dark Blue": {"mode": "dark", "theme": "blue"},
    "Dark Green": {"mode": "dark", "theme": "green"},
    "Light Pink": {"mode": "light", "theme": PINK_LIGHT},
    "Dark Pink": {"mode": "dark", "theme": PINK_DARK}
}
FONTS = ["Segoe UI", "Consolas", "Courier New", "Arial", "Tahoma", "Verdana"]
DEFAULT_KEYBINDS = {
    "Open PDF": "ctrl+p",
    "Close Tab": "ctrl+w",
    "Export PDFs": "ctrl+e",
    "Reset": "ctrl+r",
    "Quit": "ctrl+q",
    "Search Logs": "ctrl+f",
    "Undo Last Export": "ctrl+shift+z"
}
DEFAULT_SETTINGS = {
    "font_family": "Segoe UI",
    "font_size": 12,
    "theme": "Light Blue",
    "export_folder": "",
    "retain_client_name": False,
    "remove_blank_pages": True,
    "export_log_enabled": True,
    "auto_restore_session": True,
    "tutorial_shown": False
}
SORT_MODES = [
    "Date ↑", "Date ↓",
    "A → Z", "Z → A"
]

debug_log = []

def debug(*args, **kwargs):
    timestamp = datetime.datetime.now().strftime("[%H:%M:%S]")
    message = " ".join(str(arg) for arg in args)
    full_message = f"{timestamp} {message}"
    debug_log.append(full_message)
    print(full_message)
def create_light_pink_theme(self):
        if not PINK_LIGHT.exists():
            pink_theme = {
                "CTk": {
                    "fg_color": ["#fdf0f5", "#1e1e1e"],
                    "bg_color": "#fdf0f5"
                },
                "CTkButton": {
                    "fg_color": "#ff69b4",
                    "hover_color": "#ff85c1",
                    "text_color": "#ffffff",
                    "text_color_disabled": "#aaaaaa",
                    "corner_radius": 8,
                    "border_width": 0,
                    "border_color": "transparent"
                },
                "CTkLabel": {
                    "text_color": "#1e1e1e",
                    "text_color_disabled": ["#888888", "#666666"],
                    "fg_color": "transparent",
                    "corner_radius": 0
                },
                "CTkFrame": {
                    "fg_color": "#fdf0f5",
                    "top_fg_color": "#fdf0f5",
                    "border_color": "#ffb6c1",
                    "border_width": 0,
                    "corner_radius": 10
                },
                "CTkEntry": {
                    "fg_color": "#ffffff",
                    "border_color": "#ffb6c1",
                    "text_color": "#000000",
                    "text_color_disabled": ["#888888", "#666666"],
                    "placeholder_text_color": "#999999",
                    "border_width": 2,
                    "corner_radius": 6
                },
                "CTkOptionMenu": {
                    "fg_color": "#ffffff",
                    "button_color": "#ff69b4",
                    "button_hover_color": "#ff85c1",
                    "text_color": "#000000",
                    "dropdown_fg_color": "#ffffff",
                    "dropdown_hover_color": "#ffe4ec",
                    "corner_radius": 6,
                    "text_color_disabled": ["#888888", "#666666"]
                },
                "CTkCheckBox": {
                    "corner_radius": 6,
                    "border_width": 0,
                    "fg_color": ["#f7d6e0", "#3a3a3a"],
                    "border_color": ["#e75480", "#ff8fb3"],
                    "hover_color": "#ffc0cb",
                    "checkmark_color": "#000000",
                    "text_color": ["#000000", "#ffffff"],
                    "text_color_disabled": ["#888888", "#666666"]
                },
                "CTkSlider": {
                    "fg_color": "#ff69b4",
                    "bg_color": ["transparent", "#FDEFF4"],
                    "progress_color": "#ff69b4",
                    "button_color": "#ffb6c1",
                    "button_hover_color": "#ffa6c9",
                    "border_color": "#e6a8d7",
                    "button_corner_radius": 10,
                    "border_width": 0,
                    "corner_radius": 10,
                    "hover": True,
                    "button_length": 20
                },
                "CTkSwitch": {
                    "text_color": ["#1e1e1e", "#ffffff"],
                    "text_color_disabled": ["#999999", "#666666"],
                    "button_color": "#ffffff",
                    "button_hover_color": "#ffe4ec",
                    "progress_color": "#ff69b4",
                    "fg_color": "#d3d3d3",
                    "corner_radius": 6,
                    "border_width": 1,
                    "button_length": 5
                },
                "CTkSegmentedButton": {
                    "fg_color": "#fdf0f5",
                    "selected_color": "#ff69b4",
                    "selected_hover_color": "#ff85c1",
                    "unselected_color": "#ffffff",
                    "unselected_hover_color": "#ffe4ec",
                    "text_color": "#000000",
                    "text_color_disabled": ["#888888", "#666666"],
                    "corner_radius": 6
                },
                "CTkFont": {
                    "family": "Segoe UI",
                    "size": 13,
                    "weight": "normal"
                },
                "DropdownMenu": {
                    "fg_color": "#ffffff",
                    "hover_color": "#ffe4ec",
                    "text_color": "#000000",
                    "border_color": "#ffb6c1",
                    "border_width": 0,
                    "corner_radius": 6
                },
                "CTkScrollbar": {
                    "fg_color": ["#f7d6e0", "#2a2a2a"],
                    "button_color": ["#e75480", "#ff8fb3"],
                    "button_hover_color": ["#ffaec9", "#ff69b4"],
                    "corner_radius": 6,
                    "border_spacing": 4
                },
                "CTkScrollableFrame": {
                    "label_fg_color": ["#f7d6e0", "#2a2a2a"]
                }
            }

            with open(PINK_LIGHT, "w", encoding="utf-8") as f:
                json.dump(pink_theme, f, indent=2)
def create_dark_pink_theme(self):
    if not PINK_DARK.exists():
        dark_theme = {
        "CTk": {
            "fg_color": ["#1e1e1e", "#1e1e1e"],
            "bg_color": "#1e1e1e"
        },
        "CTkButton": {
            "fg_color": "#ff69b4",
            "hover_color": "#ff85c1",
            "text_color": "#ffffff",
            "text_color_disabled": "#aaaaaa",
            "corner_radius": 8,
            "border_width": 1,
            "border_color": "#1e1e1e"
        },
        "CTkLabel": {
            "text_color": "#ffffff",
            "text_color_disabled": ["#aaaaaa", "#666666"],
            "fg_color": "transparent",
            "corner_radius": 0
        },
        "CTkFrame": {
            "fg_color": "#292929",
            "top_fg_color": "#292929",
            "border_color": "#ff85c1",
            "border_width": 0,
            "corner_radius": 10
        },
        "CTkEntry": {
            "fg_color": "#2e2e2e",
            "border_color": "#ff8fb3",
            "text_color": "#ffffff",
            "text_color_disabled": ["#888888", "#666666"],
            "placeholder_text_color": "#bbbbbb",
            "border_width": 2,
            "corner_radius": 6
        },
        "CTkOptionMenu": {
            "fg_color": "#2e2e2e",
            "button_color": "#ff69b4",
            "button_hover_color": "#ff85c1",
            "text_color": "#ffffff",
            "dropdown_fg_color": "#1e1e1e",
            "dropdown_hover_color": "#ff85c1",
            "corner_radius": 6,
            "text_color_disabled": ["#aaaaaa", "#666666"]
        },
        "CTkCheckBox": {
            "corner_radius": 6,
            "border_width": 1,
            "fg_color": "#ff69b4",
            "border_color": "#ff85c1",
            "hover_color": "#ff69b4",
            "checkmark_color": "#ffffff",
            "text_color": "#ffffff",
            "text_color_disabled": ["#888888", "#666666"]
        },
        "CTkSlider": {
            "fg_color": "#3a3a3a",
            "bg_color": ["transparent", "#1a1a1a"],
            "progress_color": "#ff69b4",
            "button_color": "#ff85c1",
            "button_hover_color": "#ffa6c9",
            "border_color": "#e6a8d7",
            "button_corner_radius": 10,
            "border_width": 0,
            "corner_radius": 10,
            "hover": True,
            "button_length": 20
        },
        "CTkSwitch": {
            "text_color": ["#ffffff", "#ffffff"],
            "text_color_disabled": ["#999999", "#666666"],
            "button_color": "#ff69b4",
            "button_hover_color": "#ff85c1",
            "progress_color": "#ff85c1",
            "fg_color": "#444444",
            "corner_radius": 6,
            "border_width": 1,
            "button_length": 5
        },
        "CTkSegmentedButton": {
            "fg_color": "#2a2a2a",
            "selected_color": "#ff69b4",
            "selected_hover_color": "#ff85c1",
            "unselected_color": "#333333",
            "unselected_hover_color": "#ffb6c1",
            "text_color": "#ffffff",
            "text_color_disabled": ["#aaaaaa", "#666666"],
            "corner_radius": 6
        },
        "CTkFont": {
            "family": "Segoe UI",
            "size": 13,
            "weight": "normal"
        },
        "DropdownMenu": {
            "fg_color": "#2e2e2e",
            "hover_color": "#ff85c1",
            "text_color": "#ffffff",
            "border_color": "#ffb6c1",
            "border_width": 1,
            "corner_radius": 6
        },
        "CTkScrollbar": {
            "fg_color": ["#3a3a3a", "#2a2a2a"],
            "button_color": ["#e75480", "#ff8fb3"],
            "button_hover_color": ["#ffaec9", "#ff69b4"],
            "corner_radius": 6,
            "border_spacing": 4
        },
        "CTkScrollableFrame": {
            "label_fg_color": ["#3a3a3a", "#2a2a2a"]
        }
    }

        with open(PINK_DARK, "w", encoding="utf-8") as f:
            json.dump(dark_theme, f, indent=2)

# ───── MAIN APPLICATION ─────
class PDFSplitterApp(TkinterDnD.Tk):
    # ─── INITIALIZATION ───
    def __init__(self):
        super().__init__()
        self.pdf_sessions = {}

        # Load license info
        if LICENSE_FILE.exists():
            with open(LICENSE_FILE, "r") as f:
                license_data = json.load(f)
            self.licensed_company = license_data.get("company", "Unknown")
            self.title(f"CleanCutPDF – Licensed to {self.licensed_company}")
        else:
            self.licensed_company = "Unlicensed"
            self.title("CleanCutPDF")
        self.geometry("900x600")
        self.update_idletasks()
        self.state("zoomed")
        self.suppress_autofill = False

        self.show_loading_overlay()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        if not self.check_license():
            self.destroy()
            return

        self.after(500, self.finish_initialization)
    def finish_initialization(self):
        self.settings = {}
        self.load_settings()
        create_light_pink_theme(self)
        create_dark_pink_theme(self)

        self.reader = None
        self.ranges = []
        self.entries = []
        self.last_exported_files = []
        self.setting_keybind = False
        self.active_keybind_target = None
        self.debug_console_window = None
        self.debug_output_stream = None

        self.theme = self.settings.get("theme", "Light Blue")
        theme_config = THEMES.get(self.theme, {"mode": "light", "theme": "blue"})
        ctk.set_appearance_mode(theme_config["mode"])
        ctk.set_default_color_theme(theme_config["theme"])

        self.font_size = self.settings.get("font_size", 12)
        self.font_family = self.settings.get("font_family", "Segoe UI")

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

        self.hide_loading_overlay()

        if self.settings.get("auto_restore_session", True):
            self.restore_previous_session()
        self.start_auto_save_sessions()

    # ─── Loading UI ───
    def show_loading_overlay(self, message="Loading..."):
        if hasattr(self, "loading_overlay") and self.loading_overlay and self.loading_overlay.winfo_exists():
            return  # Already visible

        # ─── Theme-Aware Colors ───
        theme = ctk.ThemeManager.theme

        # Background color
        bg_color = theme["CTk"]["fg_color"]
        if isinstance(bg_color, list):
            bg_color = bg_color[0] if ctk.get_appearance_mode() == "Light" else bg_color[1]

        # Dot colors
        # Button color may be a list (light/dark mode)
        active_color = theme.get("CTkButton", {}).get("fg_color", "#ff69b4")
        if isinstance(active_color, list):
            active_color = active_color[0] if ctk.get_appearance_mode() == "Light" else active_color[1]

        inactive_color = theme.get("CTkLabel", {}).get("text_color_disabled", "#aaaaaa")
        if isinstance(inactive_color, list):
            inactive_color = inactive_color[0] if ctk.get_appearance_mode() == "Light" else inactive_color[1]

    # ─── Overlay Window ───
        self.loading_overlay = tk.Toplevel(self)
        self.loading_overlay.overrideredirect(True)
        self.loading_overlay.configure(bg=bg_color)
        self.loading_overlay.attributes("-topmost", True)

        # Center the overlay
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        overlay_w = 240
        overlay_h = 120
        x = (screen_w - overlay_w) // 2
        y = (screen_h - overlay_h) // 2
        self.loading_overlay.geometry(f"{overlay_w}x{overlay_h}+{x}+{y}")

        # ─── Canvas for Dots ───
        canvas = tk.Canvas(self.loading_overlay, bg=bg_color, highlightthickness=0, width=overlay_w, height=overlay_h)
        canvas.pack(fill="both", expand=True)

        dot_radius = 10
        spacing = 40
        start_x = (overlay_w - spacing * 2) // 2
        y_pos = overlay_h // 2

        self.loading_dots = []
        for i in range(3):
            x = start_x + i * spacing
            dot = canvas.create_oval(
                x - dot_radius, y_pos - dot_radius,
                x + dot_radius, y_pos + dot_radius,
                fill=inactive_color,
                outline=""
            )
            self.loading_dots.append(dot)

        self.loading_dot_index = 0

        # ─── Animation Loop ───
        def animate():
            if not self.loading_overlay.winfo_exists():
                return

            for i, dot in enumerate(self.loading_dots):
                color = active_color if i == self.loading_dot_index else inactive_color
                canvas.itemconfig(dot, fill=color)

            self.loading_dot_index = (self.loading_dot_index + 1) % len(self.loading_dots)
            self.loading_overlay.after(300, animate)

        animate()
    def hide_loading_overlay(self):
        if hasattr(self, 'loading_overlay') and self.loading_overlay.winfo_exists():
            self.loading_overlay.destroy()
    def _show_brief_loading_overlay(self):
        self.show_loading_overlay()
        self.after(400, self.hide_loading_overlay)
    def show_fullscreen_loading_overlay(self):
        self.loading_overlay = tk.Toplevel(self)
        self.loading_overlay.overrideredirect(True)
        self.loading_overlay.attributes('-topmost', True)
        self.loading_overlay.grab_set()

        # Match the size of the app window
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = self.winfo_rootx()
        y = self.winfo_rooty()
        self.loading_overlay.geometry(f"{width}x{height}+{x}+{y}")

        # Use theme background
        bg_color = ctk.ThemeManager.theme.get("CTk", {}).get("fg_color", "#1e1e1e")
        if isinstance(bg_color, list):
            bg_color = bg_color[0] if ctk.get_appearance_mode() == "Light" else bg_color[1]

        self.loading_overlay.configure(bg=bg_color)

        # Dot animation canvas
        canvas = tk.Canvas(self.loading_overlay, bg=bg_color, highlightthickness=0)
        canvas.place(relx=0.5, rely=0.5, anchor="center", width=120, height=40)

        dot_radius = 6
        spacing = 30
        dots = []
        for i in range(3):
            x = i * spacing + 10
            dot = canvas.create_oval(x, 10, x + dot_radius, 10 + dot_radius, fill="#ff69b4", outline="")
            dots.append(dot)

        def animate(index=0):
            for i, dot in enumerate(dots):
                color = "#ff69b4" if i == index else "#888888"
                canvas.itemconfig(dot, fill=color)
            self.loading_overlay.after(200, animate, (index + 1) % 3)

        animate()

    # ─── Settings ───
    def load_settings(self):
        self.settings = DEFAULT_SETTINGS.copy()
        try:
            with open(SETTINGS_FILE, "r") as f:
                user_settings = json.load(f)

            if not isinstance(user_settings, dict):
                raise ValueError("Invalid settings format")

            # Merge user settings into default
            self.settings.update(user_settings)


        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            debug("[DEBUG] Creating fresh settings.json with default values")

        # Always save back a complete version (including any new keys)
        self.save_settings()

        if not self.settings.get("tutorial_shown", False):
            self.start_tutorial()

        # Load keybinds (same logic as before)
        try:
            with open(KEYBINDS_FILE, "r") as f:
                file_keybinds = json.load(f)
                if not isinstance(file_keybinds, dict):
                    raise ValueError("Keybinds file must be a dictionary")
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            debug("[DEBUG] Generating default keybinds")
            file_keybinds = {}

        self.keybindings = {**DEFAULT_KEYBINDS, **file_keybinds}

        if self.keybindings != file_keybinds:
            with open(KEYBINDS_FILE, "w") as f:
                json.dump(self.keybindings, f, indent=2)
    def save_settings(self):
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(self.settings, f, indent=2)
    def save_sessions(self):
        data = []
        for name, session in self.pdf_sessions.items():
            parts_data = []
            for entry in session["entries"]:
                parts_data.append({
                    "range": entry["range"],  # {start: X, end: Y}
                    "revoked": entry["revoked"].get(),
                    "agency": entry["agency"].get(),
                    "description": entry["description"].get(),
                    "date": entry["date"].get()
                })

            data.append({
                "file_path": str(session["path"]),
                "client_name": session["client_name_var"].get(),
                "parts": parts_data
            })

        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        debug(f"[DEBUG] Saved {len(data)} session(s) to {SESSION_FILE}")
    def _on_close(self):
        self.save_sessions()
        debug("[DEBUG] Saving sessions")
        self.destroy()
    def restore_previous_session(self):
        if not self.settings.get("auto_restore_session", True):
            return

        if not SESSION_FILE.exists():
            return

        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                sessions = json.load(f)
            if not sessions:
                return

            for item in sessions:
                path = item.get("file_path")
                client_name = item.get("client_name", "")
                parts = item.get("parts", [])

                if not path or not Path(path).exists():
                    continue

                pdf_name = Path(path).stem
                if pdf_name in self.pdf_sessions:
                    continue  # Already restored

                reader = PdfReader(path)
                ranges = [p["range"] for p in parts] if parts else self.detect_split_ranges_from_reader(reader)

                tab = self.pdf_tabview.add(pdf_name)
                session = {
                    "tab": tab,
                    "reader": reader,
                    "path": Path(path),
                    "ranges": ranges,
                    "entries": [],
                    "client_name_var": ctk.StringVar(value=client_name),
                    "last_exported_files": [],
                    "widgets_to_scale": []
                }
                self.pdf_sessions[pdf_name] = session

                # Populate the tab’s UI
                self.render_splitter_tab(tab, session)

                # Fill restored data (must be after render_splitter_tab)
                self.suppress_autofill = True
                for i, entry_data in enumerate(parts):
                    if i >= len(session["entries"]):
                        break
                    session["entries"][i]["revoked"].set(entry_data.get("revoked", False))
                    session["entries"][i]["agency"].set(entry_data.get("agency", ""))
                    session["entries"][i]["description"].set(entry_data.get("description", "POA"))
                    session["entries"][i]["date"].set(entry_data.get("date", ""))
                self.suppress_autofill = False

        except Exception as e:
            messagebox.showwarning("Session Restore Failed", str(e))
            debug(f"[DEBUG] Session restore error: {e}")

    # ─── Tab Builders ───
    def build_splitter_tab(self):
        wrapper = ctk.CTkFrame(self.splitter_tab)
        wrapper.pack(fill="both", expand=True)

        self.splitter_wrapper = wrapper  # Store for access later

        # Enable drag-and-drop on wrapper
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.handle_drop)

        self.pdf_tabview = ctk.CTkTabview(wrapper)
        self.pdf_tabview.pack(fill="both", expand=True)

        self.add_plus_tab()
        self.enable_tab_closing()
    def build_settings_tab(self):
        ctk.CTkButton(
            self.settings_tab,
            text="🧹 Clear License Key",
            fg_color="#cc4b4b",
            hover_color="#aa2b2b",
            text_color="#ffffff",
            command=self.clear_license_and_exit
        ).pack(pady=(20, 0))

        # ─── Appearance Settings ───
        ctk.CTkLabel(self.settings_tab, text="Appearance", font=(self.font_family, self.font_size + 5)).pack(pady=(20, 0))

        # Theme selection
        self.theme_var = ctk.StringVar(value=self.theme)
        theme_menu = ctk.CTkOptionMenu(
            self.settings_tab,
            values=list(THEMES.keys()),
            variable=self.theme_var,
            command=self.change_theme
        )
        theme_menu.pack(pady=5)

        # Font size
        ctk.CTkLabel(self.settings_tab, text="Font Size").pack(pady=(10, 0))
        self.font_size_var = ctk.IntVar(value=self.font_size)
        self.font_slider = ctk.CTkSlider(
            self.settings_tab, from_=12, to=22,
            variable=self.font_size_var, number_of_steps=10,
            command=self.update_font_size
        )
        self.font_slider.pack(pady=5)

        # Font family
        ctk.CTkLabel(self.settings_tab, text="Font Family").pack(pady=(10, 0))
        self.font_family_var = ctk.StringVar(value=self.font_family)
        font_menu = ctk.CTkOptionMenu(
            self.settings_tab,
            values=FONTS,
            variable=self.font_family_var,
            command=self.update_font_family
        )
        font_menu.pack(pady=5)

        # ─── Export Settings ───
        ctk.CTkLabel(self.settings_tab, text="Export Settings", font=(self.font_family, self.font_size + 5)).pack(pady=(20, 0))

        # Export folder
        ctk.CTkLabel(self.settings_tab, text="Default Export Folder").pack(pady=(5, 0))
        self.export_folder_var = ctk.StringVar(value=self.settings.get("export_folder", "Not Set"))
        export_frame = ctk.CTkFrame(self.settings_tab)
        export_frame.pack(pady=5, padx=20, fill="x")

        self.export_display = ctk.CTkEntry(export_frame, textvariable=self.export_folder_var, state="disabled")
        self.export_display.pack(side="left", fill="x", expand=True, padx=(0, 10))


        browse_button = ctk.CTkButton(export_frame, text="📁 Browse...", command=self.set_export_folder)
        browse_button.pack(side="left")

        # Retain client name toggle
        self.settings.setdefault("retain_client_name", False)
        self.retain_client_var = ctk.BooleanVar(value=self.settings.get("retain_client_name", False))
        ctk.CTkCheckBox(
            self.settings_tab,
            text="Retain Client Name Between Files",
            variable=self.retain_client_var,
            command=self.update_retain_client_setting
        ).pack(pady=5)

        # Export log toggle
        self.export_log_var = ctk.BooleanVar(value=self.settings.get("export_log_enabled", True))
        ctk.CTkCheckBox(
            self.settings_tab,
            text="Generate Export Log",
            variable=self.export_log_var,
            command=self.update_export_log_setting
        ).pack(pady=5)

        # ─── Behavior Options ───
        ctk.CTkLabel(self.settings_tab, text="Behavior Options", font=(self.font_family, self.font_size + 5)).pack(pady=(20, 0))

        self.remove_blank_var = ctk.BooleanVar(value=self.settings.get("remove_blank_pages", True))
        ctk.CTkCheckBox(
            self.settings_tab,
            text="Remove Blank Pages Automatically",
            variable=self.remove_blank_var,
            command=self.update_remove_blank_setting
        ).pack(pady=5)
        # Auto-restore session toggle
        self.auto_restore_var = ctk.BooleanVar(value=self.settings.get("auto_restore_session", True))
        ctk.CTkCheckBox(
            self.settings_tab,
            text="Auto-Restore Previous Session on Launch",
            variable=self.auto_restore_var,
            command=self.update_auto_restore_setting
        ).pack(pady=5)

        ctk.CTkButton(self.settings_tab, text="📘 Run Tutorial Again", command=self.start_tutorial).pack(pady=(10, 0))
    def build_about_tab(self):
        scroll_frame = ctk.CTkScrollableFrame(self.about_tab)
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Inner wrapper frame to center content
        inner_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        inner_frame.pack(anchor="center", pady=10)

        text = (
            f"CleanCutPDF v1.4 – “The Refined Edge”\n"
            f"Licensed to: {self.licensed_company}\n\n"
            "CleanCutPDF is a responsive, customizable tool for cleanly and efficiently splitting PDF documents.\n\n"
            "New in Version 1.4:\n"
            "• Automatic session saving and restoration\n"
            "• Multi-tab PDF editing (open multiple PDFs at once)\n"
            "• Tab closing support (right-click or Ctrl+W)\n"
            "• First-time user tutorial walkthrough\n"
            "• Drag-and-drop batch file support\n"
            "• Improved autofill with overwrite protection\n"
            "• Logs now grouped by date for easier reading\n"
            "• Splitter layout polish and alignment fixes\n"
            "• New settings: client name retention, folder creation toggle\n"
            "• Minor bug fixes and UI consistency improvements\n\n"
            "Key Features:\n"
            "• Drag-and-drop PDF support\n"
            "• Auto-detects split markers (e.g., 'SPLIT HERE')\n"
            "• Metadata-driven filename generation (Agency, Description, Date)\n"
            "• Smart title casing with acronym protection (LLC, INC, etc.)\n"
            "• Blank page removal (optional)\n"
            "• Export folder customization with per-client subfolders\n"
            "• Export log with undo, search, sort, and highlights\n"
            "• Tab-based multi-PDF workflow and closing support\n"
            "• Fully customizable font, theme, and keybindings\n"
            "• First-launch guided tutorial system\n"
            "• Built-in debug console for real-time logging\n\n"
            "Your preferences are saved to your user directory (.cleancutpdf).\n\n"
            "Designed by Ethan Brothers\n"
            "© 2025 — Version 1.4"
        )

        self.about_label = ctk.CTkLabel(
            inner_frame,
            text=text,
            justify="center",
            anchor="center",
            wraplength=700,
            font=(self.font_family, self.font_size)
        )
        self.about_label.pack(pady=10)
    def build_log_tab(self):
        search_frame = ctk.CTkFrame(self.log_tab)
        search_frame.pack(fill="x", padx=10, pady=10)

        self.search_var = ctk.StringVar()
        self.sort_mode_var = ctk.StringVar(value="Date ↓")

        ctk.CTkLabel(search_frame, text="Search:").pack(side="left", padx=(0, 5))
        self.search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.bind("<KeyRelease>", self.update_log_view)

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

        is_light = ctk.get_appearance_mode() == "Light"

        appearance = ctk.get_appearance_mode()
        if appearance == "Light":
            log_bg = "#fff0f5"  # or match your theme color
            log_fg = "#000000"
            insert_color = "#000000"
        else:
            log_bg = "#1e1e1e"
            log_fg = "white"
            insert_color = "white"

        self.log_textbox = tk.Text(
            log_text_frame,
            wrap="word",
            bg=log_bg,
            fg=log_fg,
            insertbackground=insert_color,
            borderwidth=0,
            highlightthickness=0
        )
        self.log_textbox.pack(fill="both", expand=True)
        self.log_textbox.config(state="disabled")

        is_light = ctk.get_appearance_mode() == "Light"

        self.log_textbox.tag_configure("date", foreground="#005A9E" if is_light else "#89CFF0")
        self.log_textbox.tag_configure("label", foreground="#444444" if is_light else "#AAAAAA")
        self.log_textbox.tag_configure("value", foreground="#000000" if is_light else "#FFFFFF")
        self.log_textbox.tag_configure("revoked", foreground="#d86da0")
        self.log_textbox.tag_configure("skipped", foreground="#cc4b4b")
        self.log_textbox.tag_configure("date_marker", foreground="#888888", font=(self.font_family, self.font_size, "bold"))

        ctk.CTkButton(search_frame, text="🧹 Clear Log", command=self.clear_log).pack(side="right", padx=(10, 0))

        self.load_full_log()
    def build_keybinds_tab(self):
        for widget in self.keybinds_tab.winfo_children():
            widget.destroy()

        self.setting_keybind = False
        self.active_keybind_target = None

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

        debug("[DEBUG] Building keybind UI for:", list(self.keybindings.keys()))

        for action, combo in self.keybindings.items():
            row = ctk.CTkFrame(scroll_frame)
            row.pack(pady=5, anchor="center")

            ctk.CTkLabel(row, text=action, width=200, anchor="w").pack(side="left", padx=(0, 10))

            var = ctk.StringVar(value=combo)
            label = ctk.CTkLabel(row, textvariable=var, width=200, corner_radius=6, fg_color="#eeeeee", text_color="black", cursor="hand2")
            label.pack(side="left", padx=(0, 10))

            self.keybind_vars[action] = var

            self.add_tooltip(label, "Double-click to change keybind")

            label.bind("<Button-1>", lambda e, a=action, lbl=label: self.start_keybind_input(a, lbl))

        ctk.CTkButton(wrapper, text="Save Keybinds", command=self.save_keybinds).pack(pady=(20, 10))
    def rebuild_ui(self):
        current_tab = self.notebook.get()

        self.notebook.destroy()
        self.notebook = ctk.CTkTabview(self)
        self.notebook.pack(fill="both", expand=True)

        self.splitter_tab = self.notebook.add("Splitter")
        self.settings_tab = self.notebook.add("Settings")
        self.log_tab = self.notebook.add("Logs")
        self.about_tab = self.notebook.add("About")
        self.keybinds_tab = self.notebook.add("Keybinds")

        self.build_splitter_tab()
        self.build_settings_tab()
        self.build_log_tab()
        self.build_about_tab()
        self.build_keybinds_tab()

        self._apply_font_size()

        try:
            self.notebook.set(current_tab)
        except:
            pass

        # ✅ Safe check
        if hasattr(self, "canvas"):
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
        font = (self.font_family, self.font_size)
        self.option_add("*Font", font)

        # Update all widgets inside all PDF sessions
        if hasattr(self, "pdf_sessions"):
            for session in self.pdf_sessions.values():
                for widget in session.get("widgets_to_scale", []):
                    try:
                        widget.configure(font=font)
                    except Exception:
                        pass

                if "parts_frame" in session:
                    self._apply_font_to_widget(session["parts_frame"], font)

        # Update other tabs (Settings, Logs, etc.)
        for tab in [self.settings_tab, self.keybinds_tab, self.about_tab]:
            for child in tab.winfo_children():
                self._apply_font_to_widget(child, font)

        # Update tab labels (Splitter/About/Settings/etc.)
        self._apply_tab_font_size()

        # Log debug console if open
        if hasattr(self, "debug_console_text"):
            self.debug_console_text.configure(font=font)
    def update_font_size(self, event=None):
        self.font_size = int(self.font_size_var.get())
        self.settings["font_size"] = self.font_size
        self.save_settings()
        self._apply_font_size()
    def change_theme(self, selected_name):
        theme_config = THEMES.get(selected_name)
        if theme_config:
            self.show_fullscreen_loading_overlay()

            self.after(50, lambda: self._apply_theme_and_rebuild(selected_name, theme_config))
    def _apply_theme_and_rebuild(self, selected_name, theme_config):
        ctk.set_appearance_mode(theme_config["mode"])
        ctk.set_default_color_theme(theme_config["theme"])

        self.settings["theme"] = selected_name
        self.theme = selected_name
        self.save_settings()

        self.rebuild_ui()
        self.theme_var.set(selected_name)

        self.after(300, self.hide_loading_overlay)
    def reset_ui(self):
        if not self.winfo_exists():
            return

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
        font=(self.font_family, self.font_size)
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
    def update_font_family(self, selected_font):
        self.font_family = selected_font
        self.settings["font_family"] = selected_font
        self.save_settings()
        self._apply_font_size()
    def get_theme_loading_colors(self):
        theme = ctk.ThemeManager.theme

        # Background color
        bg = theme["CTk"]["fg_color"]
        if isinstance(bg, list):
            bg = bg[0] if ctk.get_appearance_mode() == "Light" else bg[1]

        # Active dot color
        dot = theme.get("CTkButton", {}).get("fg_color", "#ff69b4")

        # Inactive dot color (we’ll use text_color_disabled from CTkLabel)
        disabled = theme.get("CTkLabel", {}).get("text_color_disabled", "#aaaaaa")
        if isinstance(disabled, list):
            disabled = disabled[0] if ctk.get_appearance_mode() == "Light" else disabled[1]

        return {
            "bg_color": bg,
            "dot_active": dot,
            "dot_inactive": disabled
        }
    def focus_first_restored_tab(self):
        try:
            if SESSION_FILE.exists():
                with open(SESSION_FILE, "r", encoding="utf-8") as f:
                    sessions = json.load(f)
                if sessions:
                    # Cycle through all restored tabs to force layout
                    for item in sessions:
                        path = item.get("file_path")
                        if path:
                            tab_name = Path(path).stem
                            self.pdf_tabview.set(tab_name)
                            self.update_idletasks()
                    # Return to the first tab
                    first_path = sessions[0].get("file_path")
                    if first_path:
                        tab_name = Path(first_path).stem
                        self.pdf_tabview.set(tab_name)
        except Exception as e:
            debug(f"[DEBUG] Failed to auto-focus restored tabs: {e}")

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
                with open(LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Export folder changed from '{prev}' to '{folder}'\n")

            self.load_full_log()
    def update_retain_client_setting(self):
        self.settings["retain_client_name"] = self.retain_client_var.get()
        self.save_settings()
    def start_auto_save_sessions(self):
        self.auto_save_interval = 10000
        self.save_sessions()
        self.after(self.auto_save_interval, self.start_auto_save_sessions)
    def update_auto_restore_setting(self):
        self.settings["auto_restore_session"] = self.auto_restore_var.get()
        self.save_settings()

    # ─── Log Management ───
    def load_full_log(self):
        if LOG_FILE.exists():
            with open(LOG_FILE, "r") as f:
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
                info["date"] = date_match.group(1)
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
            self.log_textbox.config(state="normal")
        self.log_textbox.delete("1.0", "end")

        last_date = None  # For grouping

        for entry in parsed:
            line = entry["raw"]

            # Extract timestamp
            date_match = re.match(r"\[(\d{4}-\d{2}-\d{2})", line)
            if date_match:
                date_str = date_match.group(1)
                if date_str != last_date:
                    # Insert date marker (e.g., "──── July 8, 2025 ────")
                    formatted = datetime.datetime.strptime(date_str, "%Y-%m-%d").strftime("──── %B %d, %Y ────")
                    self.log_textbox.insert("end", f"\n{formatted}\n", "date_marker")
                    last_date = date_str

            # Timestamp line
            full_timestamp = re.match(r"\[(.*?)\]", line)
            if full_timestamp:
                timestamp = full_timestamp.group(0) + " "
                self.log_textbox.insert("end", timestamp, "date")
                line_body = line[len(timestamp):]
            else:
                line_body = line

            # Highlight each label:value pair
            fields = re.findall(r"(\b\w+):\s*(.*?)(?=\s*\||$)", line_body)
            for label, value in fields:
                tag = "value"
                if label == "Revoked" and value.strip().lower() == "true":
                    tag = "revoked"
                elif label == "Skipped" and value.strip() != "None":
                    tag = "skipped"

                self.log_textbox.insert("end", f"{label}:", "label")
                self.log_textbox.insert("end", f" {value}  ", tag)

            self.log_textbox.insert("end", "\n")
        self.log_textbox.see("end")
        self.log_textbox.config(state="disabled")
    def clear_log(self):
        confirm = messagebox.askyesno("Clear Log", "Are you sure you want to permanently clear the entire export log?")
        if confirm:
            try:
                with open(LOG_FILE, "w", encoding="utf-8") as f:
                    f.write("")
                self.full_log_lines = []
                self.update_log_view()
                messagebox.showinfo("Log Cleared", "The export log has been successfully cleared.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear the log:\n{e}")

    # ─── PDF Load & Split ───
    def load_pdf(self):
        paths = filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
        for path in paths:
            if path.lower().endswith(".pdf"):
                self.load_pdf_from_path(path)
    def load_pdf_from_path(self, path, render=True):
        pdf_name = Path(path).stem
        if pdf_name in self.pdf_sessions:
            messagebox.showinfo("Already Loaded", f"{pdf_name} is already open.")
            return

        try:
            reader = PdfReader(path)
            ranges = self.detect_split_ranges_from_reader(reader)

            # Create a new tab inside the Splitter tabview
            tab = self.pdf_tabview.add(pdf_name)

            # Force refresh of tab layout (critical for initial render)
            self.update_idletasks()

            # Create a per-PDF session dictionary
            session = {
                "tab": tab,
                "reader": reader,
                "path": Path(path),
                "ranges": ranges,
                "entries": [],
                "client_name_var": ctk.StringVar(),
                "last_exported_files": [],
                "widgets_to_scale": []  # To be populated in render_splitter_tab()
            }

            # Store session by tab name
            self.pdf_sessions[pdf_name] = session

            # Build the full UI into the tab
            self.render_splitter_tab(tab, session)

        except Exception as e:
            messagebox.showerror("Error", str(e))
        self.pdf_tabview.set(pdf_name)
        if render:
            self.render_splitter_tab(tab, session)
    def detect_split_ranges_from_reader(self, reader):
        debug("[DEBUG] Starting detect_split_ranges")
        split_pages = []

        for idx, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            words = [w for w in re.findall(r"\S+", text) if w.strip()]
            uppercase = [w.upper() for w in words]
            debug(f"[DEBUG] Page {idx+1}: {len(words)} words")

            if any("SPLIT" in w for w in uppercase) and ("HERE" in uppercase or len(words) <= 3):
                debug(f"[DEBUG] → SPLIT marker found on page {idx+1}")
                split_pages.append(idx)

        ranges = []
        start = 0
        for sp in split_pages:
            end = sp - 1
            if start <= end:
                ranges.append({"start": start, "end": end})
            start = sp + 1

        if start < len(reader.pages):
            ranges.append({"start": start, "end": len(reader.pages) - 1})
        if not ranges:
            ranges = [{"start": 0, "end": len(reader.pages) - 1}]

        debug(f"[DEBUG] Detected split ranges: {ranges}")
        return ranges
    def detect_split_ranges(self):
        return self.detect_split_ranges_from_reader(self.reader)
    def make_autofill_handler(self, field, var, index, entries_ref):
        def handler(*_):
            value = var.get()
            for j in range(index + 1, len(self.entries)):
                if not self.entries[j][field].get():
                    entries_ref[j][field].set(value)
        return handler
    def export_pdfs(self):
        client_name = self.title_case(self.client_name_var.get().strip())
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

        for idx, entry in enumerate(self.entries, start=1):
            date_input = entry["date"].get()
            try:
                formatted_date = self.format_date(date_input)
            except ValueError as e:
                messagebox.showerror(
                    "Invalid Date",
                    f"Error in Part {idx}:\n{e}\n\nYou entered: {date_input}"
                )
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

        with open(LOG_FILE, "a", encoding="utf-8") as f:
            for line in log_lines:
                f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {line}\n")

        self.last_exported_files.append(file_path)
        self.load_full_log()

        summary = (
            f"✅ Export Complete!\n\n"
            f"• {len(self.last_exported_files) - 1} file(s) created\n"
            f"• Client: {client_name}\n"
            f"• Exported to: {out_dir}\n"
        )

        if any("Skipped: " in line for line in log_lines):
            total_skipped = sum(
                len(re.search(r"Skipped: (\[.*?\])", line).group(1).split(","))
                for line in log_lines if "Skipped: [" in line
            )
            summary += f"• Blank pages skipped: {total_skipped}\n"

        messagebox.showinfo("Export Summary", summary)

        self.label_status.configure(text=f"Exported to: {out_dir}")
        self.after(50, self.reset_ui)
    def handle_drop(self, event):
        # Handles: '{C:/file1.pdf} {C:/file2.pdf}' or plain 'C:/file.pdf'
        paths = [p.strip("{}") for p in event.data.strip().split()]
        valid_files = [p for p in paths if p.lower().endswith(".pdf")]

        if not valid_files:
            messagebox.showerror("Invalid File(s)", "Only PDF files are supported.")
            return

        for path in valid_files:
            self.load_pdf_from_path(path)
    def export_current_pdf(self):
        tab_name = self.pdf_tabview.get()
        session = self.pdf_sessions.get(tab_name)
        if session:
            self.export_pdf_session(session)
    def render_splitter_tab(self, tab_frame, session):
        for widget in tab_frame.winfo_children():
            widget.destroy()

        session["entries"] = []
        ranges = session["ranges"]

        client_frame = ctk.CTkFrame(tab_frame, fg_color="transparent")
        client_frame.pack(pady=(10, 0), padx=10, fill="x")

        ctk.CTkLabel(client_frame, text="Client Name:").pack(side="left")
        ctk.CTkEntry(client_frame, textvariable=session["client_name_var"]).pack(side="left", fill="x", expand=True)

        for idx, r in enumerate(ranges, start=1):
            frame = ctk.CTkFrame(tab_frame, fg_color="transparent")
            frame.pack(pady=10, padx=10, fill="x")

            ctk.CTkLabel(frame, text=f"Part {idx} — Pages {r['start']+1} to {r['end']+1}").grid(
                row=0, column=0, columnspan=2, sticky="w"
            )

            revoked_var = ctk.BooleanVar()
            agency_var = ctk.StringVar()
            desc_var = ctk.StringVar(value="POA")
            date_var = ctk.StringVar()

            ctk.CTkSwitch(frame, text="Revoked", variable=revoked_var).grid(row=1, column=0, sticky="w")

            ctk.CTkLabel(frame, text="Agency Code:").grid(row=2, column=0, sticky="w")
            ctk.CTkEntry(frame, textvariable=agency_var).grid(row=2, column=1)

            ctk.CTkLabel(frame, text="Description:").grid(row=3, column=0, sticky="w")
            ctk.CTkEntry(frame, textvariable=desc_var).grid(row=3, column=1)

            ctk.CTkLabel(frame, text="Date (MMDDYY):").grid(row=4, column=0, sticky="w")
            ctk.CTkEntry(frame, textvariable=date_var).grid(row=4, column=1)

            session["entries"].append({
                "range": r,
                "revoked": revoked_var,
                "agency": agency_var,
                "description": desc_var,
                "date": date_var
            })

            agency_var.trace_add("write", self.make_autofill_handler("agency", agency_var, idx - 1, session["entries"]))
            desc_var.trace_add("write", self.make_autofill_handler("description", desc_var, idx - 1, session["entries"]))
            date_var.trace_add("write", self.make_autofill_handler("date", date_var, idx - 1, session["entries"]))
            revoked_var.trace_add("write", self.make_autofill_handler("revoked", revoked_var, idx - 1, session["entries"]))

        ctk.CTkButton(tab_frame, text="Export PDFs", command=lambda: self.export_session(session)).pack(pady=10)
    def export_session(self, session):
        client_name = self.title_case(session["client_name_var"].get().strip())
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
        session["last_exported_files"] = []

        for idx, entry in enumerate(session["entries"], start=1):
            try:
                formatted_date = self.format_date(entry["date"].get())
            except ValueError as e:
                messagebox.showerror("Invalid Date", f"Error in Part {idx}:\n{e}")
                return

            writer = PdfWriter()
            r = entry["range"]
            skipped = []

            for p in range(r["start"], r["end"] + 1):
                page = session["reader"].pages[p]
                if self.settings.get("remove_blank_pages", True) and self.is_blank_page(page):
                    skipped.append(p + 1)
                    continue
                writer.add_page(page)

            agency = self.get_agency(entry["agency"].get())
            desc = self.title_case(entry["description"].get())

            parts = [client_name]
            if entry["revoked"].get():
                parts.append("Revoked")
            parts.append(f"{agency} {desc}" if agency else desc)
            parts.append(formatted_date)

            fname = "_".join(parts) + ".pdf"
            file_path = out_dir / fname

            with open(file_path, "wb") as f:
                writer.write(f)

            session["last_exported_files"].append(file_path)

            log_lines.append(
                f"Client: {client_name} | File: {fname} | Pages: {r['start']+1}-{r['end']+1} | "
                f"Skipped: {skipped if skipped else 'None'} | "
                f"Agency: {agency} | Desc: {desc} | Date: {formatted_date} | Revoked: {entry['revoked'].get()}"
            )

        # 🔸 Append to export log if enabled
        if self.settings.get("export_log_enabled", True):
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                for line in log_lines:
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"[{timestamp}] {line}\n")

            self.load_full_log()

        messagebox.showinfo("Export Complete", f"Exported to: {out_dir}")

        # 🔻 Close the tab after export
        tab_name = None
        for name, s in self.pdf_sessions.items():
            if s is session:
                tab_name = name
                break
        if tab_name:
            self.pdf_tabview.delete(tab_name)
            del self.pdf_sessions[tab_name]
    def split_paths(self, data):
        # Example: '{C:/file1.pdf} {C:/file2.pdf}'
        return [p.strip("{}") for p in data.strip().split() if p.strip()]
    def add_plus_tab(self):
        if not hasattr(self, "pdf_tabview") or not isinstance(self.pdf_tabview, ctk.CTkTabview):
            return  # Prevent crash if not yet initialized

        # Use the safest check for customtkinter's internal tab map
        existing_tabs = getattr(self.pdf_tabview, "_tabs", {})

        if "+" in existing_tabs:
            return  # "+" tab already exists

        plus_tab = self.pdf_tabview.add("+")
        self.pdf_tabview.set("+")  # Focus on the plus tab

        plus_frame = ctk.CTkFrame(plus_tab)
        plus_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(plus_frame, text="Click below to open a new PDF").pack(pady=20)
        ctk.CTkButton(plus_frame, text="➕ Open PDF", command=self.load_pdf).pack()
        ctk.CTkLabel(plus_frame, text="Or drag and drop files into this area").pack(pady=(10, 0))

    # ─── Text Utilities ───
    def is_blank_page(self, page):
        text = page.extract_text()
        if not text:
            return True
        stripped = "".join(text.split())
        return len(stripped) == 0
    def format_date(self, digits):
        if not re.fullmatch(r"\d{6}", digits):
            raise ValueError("Date must be exactly 6 digits in MMDDYY format (e.g. 032524)")

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
            raise ValueError("Date contains an invalid month or day (e.g. Feb 30 doesn't exist)")

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
        debug("[DEBUG] Title case")
        acronyms = ACRONYMS
        def replacer(match):
            txt = match.group(0)
            clean = re.sub(r'[^A-Za-z]', '', txt)
            upper = clean.upper()

            if clean == "Inc" and txt.endswith("."):
                return "Inc."
            if upper in acronyms and not txt.endswith("."):
                return upper
            if txt.isupper():
                return txt  # preserve all-uppercase
            return txt[0].upper() + txt[1:].lower()

        return re.sub(r'\w\S*', replacer, s)

    # ─── Keybinds ───
    def focus_search(self):
        debug("[DEBUG] Focusing search bar")
        self.notebook.set("Logs")
        self.search_entry.focus_set()
    def save_keybinds(self):
        self.keybindings = {action: var.get() for action, var in self.keybind_vars.items()}
        debug("[DEBUG] Saving keybindings:", self.keybindings)
        with open(KEYBINDS_FILE, "w") as f:
            json.dump(self.keybindings, f, indent=2)
        debug("[DEBUG] Keybinds written to file")
        self.apply_keybinds()
        messagebox.showinfo("Keybinds Updated", "New keybindings have been saved.")
    def apply_keybinds(self):
        debug("[DEBUG] Applying keybinds:")

        try:
            keyboard.unhook_all_hotkeys()
        except AttributeError as e:
            debug("[DEBUG] Skipped unhook_all_hotkeys due to:", e)

        for action, combo in self.keybindings.items():
            debug(f"  [BIND] {action} → {combo}")

            def make_handler(action_name, callback):
                return lambda: self._debug_keybind(action_name, callback)

            callback = self.get_action_callback(action)
            try:
                keyboard.add_hotkey(combo, make_handler(action, callback))
            except ValueError as e:
                debug(f"[DEBUG] Failed to bind {combo}: {e}")

        keyboard.add_hotkey("ctrl+alt+d", self.open_debug_console)
    def undo_last_export(self):
        debug("[DEBUG] Undo keybind triggered")
        debug("[DEBUG] Files pending undo:", self.last_exported_files)

        if not self.last_exported_files:
            messagebox.showinfo("Undo", "No export to undo.")
            return

        confirm = messagebox.askyesno(
            title="Confirm Undo",
            message="Are you sure you want to permanently delete the most recent export?\n\nThis cannot be undone."
        )

        if not confirm:
            debug("[DEBUG] Undo canceled by user")
            return

        deleted = 0
        for path in self.last_exported_files:
            try:
                if path.exists():
                    path.unlink()
                    deleted += 1

                    # Remove empty parent folder
                    if path.parent.exists() and not any(path.parent.iterdir()):
                        path.parent.rmdir()
            except Exception as e:
                messagebox.showwarning("Undo Failed", f"Could not delete: {path.name}\n{e}")
                debug(f"[DEBUG] Failed to delete {path}: {e}")

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(LOG_FILE, "a", encoding="utf-8") as f:
            if deleted > 0:
                for path in self.last_exported_files:
                    f.write(f"[{timestamp}] Undo: Deleted '{path.name}' from '{path.parent}'\n")
                debug(f"[DEBUG] Undo complete: {deleted} file(s) deleted")
                self.last_exported_files = []
            else:
                f.write(f"[{timestamp}] Undo attempted, but no files were deleted.\n")
                debug("[DEBUG] Undo attempted, but no files were deleted.")

        self.load_full_log()
    def _debug_keybind(self, action_name, callback):
        if self.setting_keybind:
            debug(f"[DEBUG] Ignored keybind '{action_name}' while setting new key")
            return
        debug(f"[DEBUG] Keybind triggered: {action_name}")
        callback()
    def start_keybind_input(self, action, label_widget):
        debug(f"[DEBUG] Starting keybind input for: {action}")
        self.setting_keybind = True
        self.active_keybind_target = action

        label_widget.configure(text="Press key combo...", text_color="gray")

        recorded_keys = set()

        def on_key_event(event):
            if event.event_type == "down":
                recorded_keys.add(event.name.lower())
            elif event.event_type == "up":
                if recorded_keys:
                    combo = "+".join(sorted(recorded_keys))
                    debug(f"[DEBUG] Captured keybind for {action}: {combo}")
                    self.keybind_vars[action].set(combo)

                    keyboard.unhook_all()
                    self.setting_keybind = False
                    self.active_keybind_target = None
                    self.apply_keybinds()

        keyboard.hook(on_key_event)
    def get_action_callback(self, action):
        return {
            "Open PDF": self.load_pdf,
            "Export PDFs": self.export_pdfs,
            "Reset": self.reset_ui,
            "Quit": self.quit,
            "Search Logs": self.focus_search,
            "Undo Last Export": self.undo_last_export,
            "Clear Log": self.clear_log,
            "Close Tab": self.close_current_tab,
            "Focus Client Name": lambda: self.client_name_entry.focus_set() if self.client_name_entry else None,
            "Focus First Part": lambda: self.entries[0]["agency"].trace_info() if self.entries else None,
            "Select Export Folder": self.set_export_folder
        }.get(action, lambda: None)
    def unbind_all_keys(self):
        for combo in self.keybindings.values():
            try:
                self.unbind_all(f"<{combo}>")
                debug(f"[DEBUG] Temporarily unbound: <{combo}>")
            except Exception as e:
                debug(f"[DEBUG] Failed to unbind <{combo}>: {e}")
    def enable_tab_closing(self):
        # Must delay until widgets exist
        self.after(100, self._bind_tab_close_events)
    def _bind_tab_close_events(self):
        try:
            for name, button in self.pdf_tabview._segmented_button._buttons_dict.items():
                # Avoid rebinding multiple times
                button.unbind("<Button-3>")
                button.bind("<Button-3>", lambda e, tab=name: self._on_tab_right_click(tab))
        except Exception as e:
            debug(f"[DEBUG] Failed to bind right-click to tabs: {e}")
    def _on_tab_right_click(self, tab_name):
        if tab_name == "+":
            return

        confirm = messagebox.askyesno("Close Tab", f"Close '{tab_name}'?")
        if confirm:
            self.pdf_tabview.delete(tab_name)
            if tab_name in self.pdf_sessions:
                del self.pdf_sessions[tab_name]
                self.save_sessions()

            self.enable_tab_closing()
    def close_current_tab(self):
        tab = self.pdf_tabview.get()
        if tab == "+":
            return

        confirm = messagebox.askyesno("Close Tab", f"Close '{tab}'?")
        if confirm:
            self.pdf_tabview.delete(tab)
            if tab in self.pdf_sessions:
                del self.pdf_sessions[tab]
                self.save_sessions()
            self.enable_tab_closing()
    def enhance_entry_keybinds(self, entry_widget):
        def delete_word_left(event):
            pos = entry_widget.index("insert")
            text = entry_widget.get()
            before = text[:pos]
            after = text[pos:]
            # Remove word before cursor
            new_before = re.sub(r'\s*\S+\s*$', '', before)
            entry_widget.delete(0, "end")
            entry_widget.insert(0, new_before + after)
            entry_widget.icursor(len(new_before))
            return "break"

        def delete_word_right(event):
            pos = entry_widget.index("insert")
            text = entry_widget.get()
            before = text[:pos]
            after = text[pos:]
            # Remove word after cursor
            new_after = re.sub(r'^\s*\S+\s*', '', after)
            entry_widget.delete(0, "end")
            entry_widget.insert(0, before + new_after)
            entry_widget.icursor(len(before))
            return "break"

        entry_widget.bind("<Control-BackSpace>", delete_word_left)
        entry_widget.bind("<Control-Delete>", delete_word_right)

    # ─── Debug Window ───
    def open_debug_console(self):

        if self.debug_console_window and self.debug_console_window.winfo_exists():
            self.debug_console_window.lift()
            return

        self.debug_console_window = tk.Toplevel(self)
        self.debug_console_window.title("Debug Console")
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        width = int(screen_width * 0.6)
        height = int(screen_height * 0.4)
        x = int((screen_width - width) / 2)
        y = int((screen_height - height) / 2)

        self.debug_console_window.geometry(f"{width}x{height}+{x}+{y}")

        appearance = ctk.get_appearance_mode()
        is_light = appearance == "Light"

        if is_light:
            bg_color = "#fdf0f5" if self.theme == "Light Sydney" else "#ffffff"
            fg_color = "#000000"
            insert_color = "#000000"
        else:
            bg_color = "#1e1e1e"
            fg_color = "#00ff00"
            insert_color = "#ffffff"

        self.debug_console_window.configure(bg=bg_color)

        text_area = st.ScrolledText(
            self.debug_console_window,
            wrap="word",
            bg=bg_color,
            fg=fg_color,
            insertbackground=insert_color,
            font=(self.font_family, self.font_size),
            borderwidth=0
        )
        text_area.pack(expand=True, fill="both")

        text_area.tag_config("debug", foreground="#3366cc")
        text_area.tag_config("error", foreground="red")
        text_area.tag_config("info", foreground="green")

        for line in debug_log:
            text_area.insert("end", line + "\n")
        text_area.config(state="disabled")

        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr

        class Redirector(io.StringIO):
            def write(inner_self, text):
                text_area.config(state="normal")
                if "[ERROR]" in text:
                    text_area.insert("end", text, "error")
                elif "[DEBUG]" in text:
                    text_area.insert("end", text, "debug")
                elif "[INFO]" in text:
                    text_area.insert("end", text, "info")
                else:
                    text_area.insert("end", text)
                text_area.see("end")
                text_area.config(state="disabled")

            def flush(inner_self):
                pass

        redirect = Redirector()
        sys.stdout = sys.stderr = redirect
        self.debug_output_stream = redirect

        self.debug_console_window.protocol("WM_DELETE_WINDOW", self._close_debug_console)
    def _close_debug_console(self):
        if self.debug_output_stream:
            sys.stdout = self._original_stdout
            sys.stderr = self._original_stderr
            self.debug_output_stream = None
        self.debug_console_window.destroy()

    # ─── Tutorial ───
    def start_tutorial(self):
        steps = [
            ("Welcome to CleanCutPDF!",
             "This tutorial will guide you through the key features of the app.\n\nClick OK to begin.",
             "Splitter"),

            ("Splitter Tab",
             "This is where you drag and drop PDFs or click ➕ to load them. It automatically detects split markers.",
             "Splitter"),

            ("Editing Parts",
             "Each split part can be customized with Revoked status, Agency, Description, and Date.\nThese are used to generate filenames.",
             "Splitter"),

            ("Client Name",
             "Enter the client name once per file. The app will remember it between sessions if enabled.",
             "Splitter"),

            ("Export",
             "Click Export PDFs to generate split files into your chosen export folder. You can undo the last export if needed.",
             "Splitter"),

            ("Settings Tab",
             "In Settings, you can change the theme, font, export folder, and other preferences.",
             "Settings"),

            ("Logs",
             "The Logs tab records all exports and allows you to search and sort by client or date.",
             "Logs"),

            ("Keybinds",
             "In Keybinds, you can customize keyboard shortcuts for nearly every action.",
             "Keybinds"),

            ("You're Ready!",
             "That’s it! You can revisit this tutorial anytime by clicking 'Run Tutorial Again' in Settings.\n\nHappy splitting!",
             "Splitter")
        ]

        def show_step(index):
            if index >= len(steps):
                self.settings["tutorial_shown"] = True
                self.save_settings()
                return

            title, msg, tab = steps[index]
            self.notebook.set(tab)  # Switch tab before showing message

            # Delay slightly to ensure tab content is fully rendered before popup
            self.after(200, lambda: (
                messagebox.showinfo(title, msg),
                show_step(index + 1)
            ))

        show_step(0)
    def reset_tutorial(self):
        self.settings["tutorial_shown"] = False
        self.save_settings()
        messagebox.showinfo("Tutorial Reset", "The tutorial will run again next time you launch the app.")

    # ─── Licenses ───
    def check_license(self):
        self.hide_loading_overlay()  # Ensure popups are visible

        def debug_log(msg):
            print(f"[DEBUG] {msg}")

        def hash_key(key):
            return hashlib.sha256(key.encode("utf-8")).hexdigest()

        debug_log("Starting license check...")

        # Step 1: Check for saved license file
        if LICENSE_FILE.exists():
            debug_log(f"Found local license file at: {LICENSE_FILE}")
            try:
                with open(LICENSE_FILE, "r") as f:
                    saved = json.load(f)
                license_key = saved.get("license_key", "").strip()
                debug_log(f"Loaded cached license key: {license_key}")
            except Exception as e:
                messagebox.showerror("License Error", f"Failed to read license file:\n{e}")
                debug_log(f"Failed to load license file: {e}")
                return False
        else:
            debug_log("No license file found, prompting for key...")
            license_key = tk.simpledialog.askstring(
                "License Required", "Enter your CleanCutPDF license key:"
            )
            if not license_key:
                messagebox.showerror("License Required", "A license key is required to use this app.")
                debug_log("License entry cancelled or empty.")
                return False
            license_key = license_key.strip()

        # Step 2: Hash the entered key
        hashed_key = hash_key(license_key)
        debug_log(f"SHA-256 hash of entered key: {hashed_key}")

        # Step 3: Fetch the remote license list
        try:
            url = "https://raw.githubusercontent.com/shhmethan/CleanCutPDF/refs/heads/master1/licenses.json"
            debug_log(f"Fetching license data from: {url}")
            context = ssl._create_unverified_context()
            with urllib.request.urlopen(url, context=context) as response:
                data = json.loads(response.read())
            debug_log("Successfully fetched license list.")
        except Exception as e:
            messagebox.showerror("Network Error", f"Could not check license:\n{e}")
            debug_log(f"Failed to fetch license list: {e}")
            return False

        # Step 4: Validate hash
        valid_licenses = data.get("licenses", {})
        info = valid_licenses.get(hashed_key)

        if info:
            company = info.get("company", "Unknown Organization")
            debug_log(f"License key is valid! Company: {company}")

            # Save the license locally
            with open(LICENSE_FILE, "w") as f:
                json.dump({"license_key": license_key, "company": company}, f, indent=2)
            debug_log("License saved locally.")

            self.licensed_company = company
            self.title(f"CleanCutPDF – Licensed to {company}")
            return True
        else:
            messagebox.showerror("Invalid License", "The entered license key is not valid.")
            debug_log("No match found for hashed key. License is invalid.")
            return False
    def clear_license_and_exit(self):
        try:
            if LICENSE_FILE.exists():
                LICENSE_FILE.unlink()
                messagebox.showinfo("License Cleared", "Your license key has been removed.\nThe app will now close.")
            else:
                messagebox.showinfo("No License", "No license file was found to delete.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not delete license:\n{e}")
        self.destroy()

if __name__ == "__main__":
    app = PDFSplitterApp()
    app.mainloop()