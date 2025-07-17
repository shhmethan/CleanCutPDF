# ─── Standard Library ────────────────────────────────────────────────
import datetime
import hashlib
import io
import json
import re
import ssl
import sys
import urllib
import csv
import webbrowser
from pathlib import Path
import shutil
import tempfile
import subprocess
import os

# ─── Third-Party Libraries ───────────────────────────────────────────
import fitz
import keyboard
from PIL import Image, ImageTk
from PyPDF2 import PdfReader, PdfWriter

# ─── GUI: Tkinter & CustomTkinter ────────────────────────────────────
import tkinter as tk
import tkinter.scrolledtext as st
from tkinter import filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
import customtkinter as ctk
from customtkinter import CTkImage

# ───── CONSTANTS & CONFIG ─────
CURRENT_VERSION = "1.6.3"
VERSION_URL = "https://raw.githubusercontent.com/shhmethan/CleanCutPDF/refs/heads/master1/version.json"

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
    "Open PDF": "ctrl+o",
    "Close Tab": "ctrl+w",
    "Export PDFs": "ctrl+e",
    "Reset": "ctrl+r",
    "Quit": "ctrl+q",
    "Search Logs": "ctrl+f",
    "Undo Last Export": "ctrl+shift+z",
    "Paste Clipboard": "ctrl+shift+v"
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
    "tutorial_shown": False,
    "suppressFutureDateWarning": False
}
SORT_MODES = [
    "Date ↑", "Date ↓",
    "A → Z", "Z → A"
]

debug_log = []

def debug(message, type):
    full_message = ""
    timestamp = datetime.datetime.now().strftime("[%H:%M:%S]")
    type.lower()
    if type == "debug":
        full_message = f"{timestamp} [DEBUG] {message}"
    elif type == "warning":
        full_message = f"{timestamp} [WARNING] {message}"
    elif type == "error":
        full_message = f"{timestamp} [ERROR] {message}"
    elif type == "saved":
        full_message = f"{timestamp} [SAVED] {message}"
    elif type == "skip":
        full_message = f"{timestamp} [SKIPPED] {message}"
    elif type == "keybind":
        full_message = f"{timestamp} [KEYBIND] {message}"
    elif type == "log":
        full_message = f"{timestamp} [LOG] {message}"
    elif type == "update":
        full_message = f"{timestamp} [UPDATE] {message}"

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
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).parent / relative_path

# ───── MAIN APPLICATION ─────
def parse_version(version_str):
    return tuple(map(int, version_str.split(".")))

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

        self.finish_initialization()
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
        self.settings_widgets_to_scale = []

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
        self.quick_splitter_tab = self.notebook.add("Quick Split")
        self.settings_tab = self.notebook.add("Settings")
        self.log_tab = self.notebook.add("Logs")
        self.about_tab = self.notebook.add("About")
        self.keybinds_tab = self.notebook.add("Keybinds")
        self.help_tab = self.notebook.add("Help")

        self.build_splitter_tab()
        self.build_quick_split_tab(self.quick_splitter_tab)
        self.build_about_tab()
        self.build_settings_tab()
        self.build_log_tab()
        self.build_keybinds_tab()
        self.build_help_tab(self.help_tab)

        self._apply_font_size()
        self._apply_tab_font_size()
        self.apply_keybinds()

        self.enhance_all_entries()
        self.after(200, self.check_export_folder_prompt)

        self.hide_loading_overlay()
        self.bind_all("<Control-Shift-V>", self._handle_ctrl_shift_v)

        self.check_for_updates()
        self.cleanup_old_exe()

        self.make_client_folder_var = tk.BooleanVar(value=True)

        if self.settings.get("auto_restore_session", True):
            self.restore_previous_session()
        self.start_auto_save_sessions()
    def check_for_updates(self):
        try:
            with urllib.request.urlopen(VERSION_URL) as response:
                data = json.loads(response.read())

            remote_version = data.get("version")
            changelog = data.get("changelog", {})
            url = data.get("download_url")

            if remote_version and parse_version(remote_version) > parse_version(CURRENT_VERSION):
                debug(f"Update Available: {remote_version}", "update")

                # Get this version's changelog, or fallback
                notes_list = changelog.get(remote_version, ["No changelog available."])
                formatted = "\n".join(f"• {line}" for line in notes_list)

                confirm = messagebox.askyesno(
                    "Update Available",
                    f"A new version ({remote_version}) is available!\n\nChanges:\n{formatted}\n\nWould you like to download it now?"
                )
                if confirm:
                    self.download_and_replace_exe(url, remote_version)
            else:
                debug("App up to date.", "update")

        except Exception as e:
            debug(f"Auto-update check failed: {e}", "error")
    def download_and_replace_exe(self, url, new_version):
        try:
            temp_path = tempfile.gettempdir() + f"/cleancutpdf_update_{new_version}.exe"

            debug(f"Downloading update to: {temp_path}", "update")
            with urllib.request.urlopen(url) as response, open(temp_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)

            messagebox.showinfo("Update Ready",
                                "The new version has been downloaded.\n\nPlease close the app so it can replace the old version."
                                )

            # Schedule a script to replace after exit
            self.after(100, lambda: self.replace_on_exit(temp_path))

        except Exception as e:
            messagebox.showerror("Update Failed", f"Could not download update:\n{e}")
            debug(f"Update download failed: {e}", "error")
    def replace_on_exit(self, download_url):
        import tempfile
        import os
        import subprocess
        from pathlib import Path

        target_dir = Path(os.environ["LOCALAPPDATA"]) / "Programs" / "CleanCutPDF"
        bat_path = Path(tempfile.gettempdir()) / "cleancutpdf_update.bat"

        with open(bat_path, "w") as f:
            f.write(rf"""@echo off
    echo Downloading update...
    powershell -Command "Invoke-WebRequest '%~1' -OutFile 'pdf_splitter.update.exe'"
    
    timeout /t 1 >nul
    taskkill /f /im pdf_splitter.exe >nul 2>&1
    
    move /Y "pdf_splitter.exe" "pdf_splitter.old.exe"
    move /Y "pdf_splitter.update.exe" "pdf_splitter.exe"
    
    timeout /t 3 >nul
    
    start "" "pdf_splitter.exe"
    
    del "%~f0"
    """)

        subprocess.Popen(["cmd", "/c", str(bat_path), download_url], cwd=str(target_dir))
        self.quit()
    def cleanup_old_exe(self):
        current_exe = sys.executable
        old_exe = current_exe.replace(".exe", ".old.exe")
        if os.path.exists(old_exe):
            try:
                os.remove(old_exe)
                debug("Old version removed after successful update.", "update")
            except Exception as e:
                debug(f"Failed to delete old version: {e}", "error")

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
            debug("Creating fresh settings.json with default values", "error")

        # Always save back a complete version (including any new keys)
        self.save_settings()

        # Load keybinds (same logic as before)
        try:
            with open(KEYBINDS_FILE, "r") as f:
                file_keybinds = json.load(f)
                if not isinstance(file_keybinds, dict):
                    raise ValueError("Keybinds file must be a dictionary")
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            debug("Generating default keybinds", "error")
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
        debug(f"Saved {len(data)} session(s) to {SESSION_FILE}", "saved")
    def _on_close(self):
        self.save_sessions()
        debug("Saving sessions", "debug")
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

                tab_label = f"{pdf_name} ✖"
                tab = self.pdf_tabview.add(tab_label)

                session = {
                    "tab": tab,
                    "tab_label": tab_label,
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
            debug(f"Session restore error: {e}", "error")
    def check_future_date(self, raw_date, callback_on_confirm):
        try:
            today = datetime.date.today()
            entered_date = datetime.datetime.strptime(raw_date, "%m%d%y").date()
        except Exception:
            debug(f"Invalid date format: {raw_date}", "debug")
            return  # skip if invalid

        if entered_date <= today:
            return  # not in the future — no prompt needed

        if self.settings.get("suppressFutureDateWarning", False):
            return  # user opted out

        # Custom confirmation dialog
        popup = tk.Toplevel(self)
        bg_color = ctk.ThemeManager.theme["CTkFrame"]["fg_color"]
        popup.configure(bg=bg_color)
        popup.attributes("-topmost", True)
        popup.grab_set()
        popup.resizable(False, False)
        popup.geometry("380x160")
        popup.title("Confirm Future Date")

        # --- Widgets with font scaling ---
        ctk.CTkLabel(
            popup,
            text="This date is in the future. Are you sure?",
            font=(self.font_family, self.font_size)
        ).pack(pady=(20, 10))

        suppress_var = tk.BooleanVar()
        ctk.CTkCheckBox(
            popup,
            text="Don't show this message again",
            variable=suppress_var,
            font=(self.font_family, self.font_size)
        ).pack(pady=(0, 10))

        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.pack(pady=(0, 10))

        ctk.CTkButton(
            btn_frame, text="Yes", width=80,
            font=(self.font_family, self.font_size),
            command=lambda: on_yes()
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame, text="Cancel", width=80,
            font=(self.font_family, self.font_size),
            command=lambda: on_cancel()
        ).pack(side="left", padx=10)


        def on_yes():
            if suppress_var.get():
                self.settings["suppressFutureDateWarning"] = True
                self.save_settings()
                debug("Future date warning suppressed by user", "debug")
            popup.destroy()
            callback_on_confirm()

        def on_cancel():
            popup.destroy()

        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.pack(pady=(0, 10))

        ctk.CTkButton(btn_frame, text="Yes", width=80, command=on_yes).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", width=80, command=on_cancel).pack(side="left", padx=10)

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
        self._apply_tab_font_size()
    def build_quick_split_tab(self, tab):
        wrapper = ctk.CTkFrame(tab)
        wrapper.pack(fill="both", expand=True, padx=20, pady=20)

        wrapper.drop_target_register(DND_FILES)
        wrapper.dnd_bind('<<Drop>>', self.handle_quick_drop)


        label = ctk.CTkLabel(wrapper, text="Quick Split Mode", font=(self.font_family, self.font_size + 2))
        label.pack(pady=(10, 5))

        desc = (
            "This mode splits the PDF wherever 'SPLIT HERE' markers are found.\n"
            "No client name or metadata required.\n\n"
            "Files will be named generically (e.g., Part 1 - {original file name}.pdf, Part 2 - {original file name}.pdf) and\n"
            "saved into the folder called \"Single Split Files\""
        )
        ctk.CTkLabel(wrapper, text=desc, font=(self.font_family, self.font_size), wraplength=600, justify="center").pack(pady=10)

        open_button = ctk.CTkButton(wrapper, text="Open PDF for Quick Split", command=self.load_quick_split_pdf)
        open_button.pack(pady=10)
    def build_settings_tab(self):
        container = ctk.CTkFrame(self.settings_tab)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # Left: Vertical menu
        menu = ctk.CTkFrame(container, width=150)
        menu.pack(side="left", fill="y", padx=(0, 10))

        # Right: Content area
        self.settings_stack = ctk.CTkFrame(container)
        self.settings_stack.pack(side="left", fill="both", expand=True)

        # Create section frames
        self.settings_sections = {}

        for section in ["Appearance", "Export", "Behavior", "License"]:
            frame = ctk.CTkFrame(self.settings_stack)
            frame.pack(fill="both", expand=True)
            frame.pack_forget()  # Hide initially
            self.settings_sections[section] = frame

        # Populate each section
        self._build_appearance_section(self.settings_sections["Appearance"])
        self._build_export_section(self.settings_sections["Export"])
        self._build_behavior_section(self.settings_sections["Behavior"])
        self._build_license_section(self.settings_sections["License"])

        # Sidebar buttons
        for section in self.settings_sections:
            btn = ctk.CTkButton(menu, text=section, command=lambda s=section: self._show_settings_section(s))
            btn.pack(fill="x", pady=5)

        self._show_settings_section("Appearance")
    def build_about_tab(self):
        scroll_frame = ctk.CTkScrollableFrame(self.about_tab)
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Inner wrapper frame to center content
        inner_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        inner_frame.pack(anchor="center", pady=10)

        version_label = ctk.CTkLabel(inner_frame, text=f"CleanCutPDF Version: {CURRENT_VERSION}", font=(self.font_family, self.font_size))
        version_label.pack(pady=(10, 5))


        text = (
            f"CleanCutPDF v{CURRENT_VERSION} – “Quick Precision”\n"
            f"Licensed to: {self.licensed_company}\n\n"
            "CleanCutPDF is a responsive, customizable tool for cleanly and efficiently splitting PDF documents.\n\n"
            f"New in Version {CURRENT_VERSION}:\n"
            "• Quick Split tab for fast splitting with no renaming\n"
            "• Client folder toggle (Make Client Folder checkbox)\n"
            "• Logs now grouped by original PDF name\n"
            "• Visible 'X' close buttons on PDF tabs\n"
            "• Default export folder prompt on startup\n"
            "• Floating keybind reference overlay\n"
            "• Font scaling now applies everywhere (including tabs/logs)\n"
            "• Enhanced titlecasing (handles Vega-Albela, McFly, etc.)\n"
            "• Help tab includes SPLIT HERE download and tips\n"
            "• Improved tutorial that reflects all current UI elements\n"
            "• Ctrl+Backspace / Ctrl+Delete support in input fields\n"
            "• Drag-and-drop support for Quick Split\n"
            "• Paste now works with Ctrl+Shift+V\n\n"
            "Key Features:\n"
            "• Drag-and-drop PDF support\n"
            "• Auto-detects split markers (e.g., 'SPLIT HERE')\n"
            "• Metadata-driven filename generation (Agency, Description, Date)\n"
            "• Smart title casing with acronym protection (LLC, INC, IRS)\n"
            "• Blank page removal (optional)\n"
            "• Export folder customization with per-client subfolders\n"
            "• Export log with undo, search, filters, and highlights\n"
            "• Multi-tab PDF workflow with closeable tabs\n"
            "• Customizable theme, font, and keybindings\n"
            "• Built-in debug console and log view\n"
            "• Fully guided onboarding tutorial\n\n"
            "Your preferences are saved to your user directory (.cleancutpdf).\n\n"
            "Designed by Ethan Brothers\n"
            f"© 2025 — Version {CURRENT_VERSION}"
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

        self.log_scroll_frame = ctk.CTkScrollableFrame(self.log_tab)
        self.log_scroll_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10), anchor="n")

        ctk.CTkButton(search_frame, text="🧹 Clear Log", command=self.clear_log).pack(side="right", padx=(10, 0))
        ctk.CTkButton(search_frame, text="📤 Export to...", command=self.open_log_export_popup).pack(side="right", padx=(10, 5))

        self.load_full_log()
    def build_keybinds_tab(self):
        for widget in self.keybinds_tab.winfo_children():
            widget.destroy()

        self.setting_keybind = False
        self.active_keybind_target = None

        wrapper = ctk.CTkFrame(self.keybinds_tab, fg_color="transparent")
        wrapper.pack(anchor="n", pady=20)

        ctk.CTkLabel(wrapper, text="Custom Keybindings").pack(pady=(10, 10))

        scroll_container = ctk.CTkFrame(wrapper, width=480, height=420)
        scroll_container.pack()
        scroll_container.pack_propagate(False)

        scroll_frame = ctk.CTkScrollableFrame(scroll_container)
        scroll_frame.pack(fill="both", expand=True)

        self.keybind_vars = {}

        debug(f"Building keybind UI for: {list(self.keybindings.keys())}", "debug")

        for action, combo in self.keybindings.items():
            for idx, (action, combo) in enumerate(self.keybindings.items()):
                ctk.CTkLabel(scroll_frame, text=action, anchor="w", width=220).grid(row=idx, column=0, sticky="w", pady=4, padx=10)

                var = ctk.StringVar(value=combo)
                label = ctk.CTkLabel(
                    scroll_frame,
                    textvariable=var,
                    width=180,
                    corner_radius=6,
                    fg_color="#eeeeee",
                    text_color="black",
                    cursor="hand2"
                )
                label.grid(row=idx, column=1, sticky="e", padx=(0, 10), pady=4)

                self.keybind_vars[action] = var

                self.add_tooltip(label, "Click to change keybind")
                label.bind("<Button-1>", lambda e, a=action, lbl=label: self.start_keybind_input(a, lbl))

            self.keybind_vars[action] = var

            self.add_tooltip(label, "Double-click to change keybind")

            label.bind("<Button-1>", lambda e, a=action, lbl=label: self.start_keybind_input(a, lbl))

        ctk.CTkButton(wrapper, text="Save Keybinds", command=self.save_keybinds, fg_color="#ff69b4").pack(pady=(20, 10))
    def build_help_tab(self, tab):
        scrollable = ctk.CTkScrollableFrame(tab)
        scrollable.pack(fill="both", expand=True, padx=20, pady=20)

        content = ctk.CTkFrame(scrollable, fg_color="transparent")
        content.pack(anchor="center")

        font_title = (self.font_family, self.font_size + 3, "bold")
        font_section = (self.font_family, self.font_size + 1, "bold")
        font_body = (self.font_family, self.font_size)

        def add_spacer(height=10):
            ctk.CTkLabel(content, text="", height=height).pack()

        # SPLIT HERE Sheets
        ctk.CTkLabel(content, text="📄 Using SPLIT HERE Sheets", font=font_title, anchor="center").pack()
        add_spacer(6)
        tips = [
            "• Use brightly colored paper to make them stand out",
            "• Add tabs or sticky notes to the edges for easier removal after scanning",
            "• Clearly print 'SPLIT HERE' in large bold text (or use the template)",
            "• Place a sheet between documents, not between clients"
        ]
        for tip in tips:
            ctk.CTkLabel(content, text=tip, font=font_body, anchor="w", justify="left", wraplength=760).pack(anchor="center")

        add_spacer(14)

        # Scanner Settings
        ctk.CTkLabel(content, text="🖨️ Printer & Scanner Tips", font=font_section, anchor="center").pack()
        printer_tips = [
            "• If using tabs, enable 'multiple size originals' mode on your scanner",
            "• Position tabs so they face outward, away from the feeder side",
            "• Pre-sort into single- and double-sided batches for cleaner scans",
            "• After scanning, drag and drop your PDF into CleanCutPDF — SPLIT HERE sheets are auto-detected"
        ]
        for tip in printer_tips:
            ctk.CTkLabel(content, text=tip, font=font_body, anchor="w", justify="left", wraplength=760).pack(anchor="center")

        add_spacer(20)

        # Splitter
        ctk.CTkLabel(content, text="🧾 Using the Splitter", font=font_title, anchor="center").pack()
        add_spacer(6)
        splitter_tips = [
            "• Best for clients who have multiple documents to split and rename",
            "• Scan each client separately, with SPLIT HERE sheets between each document",
            "• Use the Splitter to rename files with agency, description, and date"
        ]
        for tip in splitter_tips:
            ctk.CTkLabel(content, text=tip, font=font_body, anchor="w", justify="left", wraplength=760).pack(anchor="center")

        add_spacer(20)

        # Quick Splitter
        ctk.CTkLabel(content, text="⚡ Using the Quick Splitter", font=font_title, anchor="center").pack()
        add_spacer(6)
        quick_tips = [
            "• Best for scanning many clients with one document each (e.g., fax packets)",
            "• Place SPLIT HERE sheets between each client’s stack",
            "• Scan everything in one go, then split in CleanCutPDF",
            "• Rename with the Splitter afterward if needed"
        ]
        for tip in quick_tips:
            ctk.CTkLabel(content, text=tip, font=font_body, anchor="w", justify="left", wraplength=760).pack(anchor="center")

        add_spacer(20)

        # Download button
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(pady=10)

        ctk.CTkButton(
            btn_frame,
            text="📥 Download SPLIT HERE Template",
            font=font_body,
            command=self.download_split_here_sheet
        ).pack()
    def rebuild_ui(self):
        current_tab = self.notebook.get()

        self.notebook.destroy()
        self.notebook = ctk.CTkTabview(self)
        self.notebook.pack(fill="both", expand=True)

        self.splitter_tab = self.notebook.add("Splitter")
        self.quick_splitter_tab = self.notebook.add("Quick Split")
        self.settings_tab = self.notebook.add("Settings")
        self.log_tab = self.notebook.add("Logs")
        self.about_tab = self.notebook.add("About")
        self.keybinds_tab = self.notebook.add("Keybinds")
        self.help_tab = self.notebook.add("Help")

        self.build_splitter_tab()
        self.build_quick_split_tab(self.quick_splitter_tab)
        self.build_settings_tab()
        self.build_log_tab()
        self.build_about_tab()
        self.build_keybinds_tab()
        self.build_help_tab(self.help_tab)

        self._apply_font_size()

        try:
            self.notebook.set(current_tab)
        except:
            pass

        # Safe check
        if hasattr(self, "canvas"):
            self._check_scrollbar_visibility()

        # Rebuild open tabs from in-memory sessions
        for pdf_name, session in self.pdf_sessions.items():
            tab_label = session["tab_label"]
            tab = self.pdf_tabview.add(tab_label)
            session["tab"] = tab
            self.render_splitter_tab(tab, session)

        # Re-apply fonts and bindings
        self._apply_tab_font_size()
        self.enable_tab_closing()

        if self.pdf_sessions:
            first_key = next(iter(self.pdf_sessions))
            self.pdf_tabview.set(self.pdf_sessions[first_key]["tab_label"])

    # ─── Settings Builder Tabs ───
    def _show_settings_section(self, name):
        for section, frame in self.settings_sections.items():
            frame.pack_forget()
        self.settings_sections[name].pack(fill="both", expand=True)
    def _build_appearance_section(self, parent):
        font = (self.font_family, self.font_size)

        label = ctk.CTkLabel(parent, text="Theme", font=font)
        label.pack(pady=(10, 5))
        self.settings_widgets_to_scale.append(label)

        self.theme_var = ctk.StringVar(value=self.theme)
        theme_menu = ctk.CTkOptionMenu(
            parent,
            values=list(THEMES.keys()),
            variable=self.theme_var,
            command=self.change_theme
        )
        theme_menu.pack(pady=5)
        self.settings_widgets_to_scale.append(theme_menu)

        label2 = ctk.CTkLabel(parent, text="Font Size", font=font)
        label2.pack(pady=(10, 0))
        self.settings_widgets_to_scale.append(label2)

        self.font_size_var = ctk.IntVar(value=self.font_size)
        font_slider = ctk.CTkSlider(
            parent, from_=12, to=22, number_of_steps=10,
            variable=self.font_size_var, command=self.update_font_size
        )
        font_slider.pack(pady=5)
        self.settings_widgets_to_scale.append(font_slider)

        label3 = ctk.CTkLabel(parent, text="Font Family", font=font)
        label3.pack(pady=(10, 0))
        self.settings_widgets_to_scale.append(label3)

        self.font_family_var = ctk.StringVar(value=self.font_family)
        font_menu = ctk.CTkOptionMenu(
            parent,
            values=FONTS,
            variable=self.font_family_var,
            command=self.update_font_family
        )
        font_menu.pack(pady=5)
        self.settings_widgets_to_scale.append(font_menu)
    def _build_export_section(self, parent):
        font = (self.font_family, self.font_size)

        label = ctk.CTkLabel(parent, text="Default Export Folder", font=font)
        label.pack(pady=(10, 5))
        self.settings_widgets_to_scale.append(label)

        self.export_folder_var = ctk.StringVar(value=self.settings.get("export_folder", "Not Set"))
        export_frame = ctk.CTkFrame(parent)
        export_frame.pack(pady=5, padx=20, fill="x")

        self.export_display = ctk.CTkEntry(export_frame, textvariable=self.export_folder_var, state="disabled")
        self.export_display.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.settings_widgets_to_scale.append(self.export_display)

        browse_button = ctk.CTkButton(export_frame, text="📁 Browse...", command=self.set_export_folder)
        browse_button.pack(side="left")
        self.settings_widgets_to_scale.append(browse_button)

        # Export log toggle
        self.export_log_var = ctk.BooleanVar(value=self.settings.get("export_log_enabled", True))
        log_box = ctk.CTkCheckBox(
            parent,
            text="Generate Export Log",
            variable=self.export_log_var,
            command=self.update_export_log_setting
        )
        log_box.pack(pady=5)
        self.settings_widgets_to_scale.append(log_box)
    def _build_behavior_section(self, parent):
        font = (self.font_family, self.font_size)

        self.remove_blank_var = ctk.BooleanVar(value=self.settings.get("remove_blank_pages", True))
        remove_blank_checkbox = ctk.CTkCheckBox(
            parent,
            text="Remove Blank Pages Automatically",
            variable=self.remove_blank_var,
            command=self.update_remove_blank_setting
        )
        remove_blank_checkbox.pack(pady=5)
        self.settings_widgets_to_scale.append(remove_blank_checkbox)

        self.auto_restore_var = ctk.BooleanVar(value=self.settings.get("auto_restore_session", True))
        auto_restore_checkbox = ctk.CTkCheckBox(
            parent,
            text="Auto-Restore Previous Session on Launch",
            variable=self.auto_restore_var,
            command=self.update_auto_restore_setting
        )
        auto_restore_checkbox.pack(pady=5)
        self.settings_widgets_to_scale.append(auto_restore_checkbox)

        tutorial_btn = ctk.CTkButton(parent, text="📘 Run Tutorial Again", command=self.start_tutorial)
        tutorial_btn.pack(pady=(20, 0))
        self.settings_widgets_to_scale.append(tutorial_btn)
    def _build_license_section(self, parent):
        font = (self.font_family, self.font_size)

        ctk.CTkLabel(parent, text="License Information", font=(self.font_family, self.font_size + 2)).pack(pady=(20, 10))

        license_key = ""
        company = self.licensed_company or "Unknown"
        masked = tk.BooleanVar(value=True)

        if LICENSE_FILE.exists():
            try:
                with open(LICENSE_FILE, "r") as f:
                    saved = json.load(f)
                    license_key = saved.get("license_key", "")
            except Exception as e:
                debug(f"Error reading license file: {e}", "error")

        def get_display_key():
            return "• " * len(license_key) if masked.get() else license_key or "N/A"

        key_var = tk.StringVar(value=get_display_key())

        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(pady=5, anchor="center")

        ctk.CTkLabel(row, text="License Key:", font=font, width=120).pack(side="left", padx=(0, 5))
        key_label = ctk.CTkLabel(row, textvariable=key_var, font=font)
        key_label.pack(side="left", padx=(0, 5))

        toggle_btn = ctk.CTkButton(row, text="Show" if masked.get() else "Hide", width=60,
                                   command=lambda: (masked.set(not masked.get()),
                                                    key_var.set(get_display_key()),
                                                    toggle_btn.configure(text="Show" if masked.get() else "Hide")))
        toggle_btn.pack(side="left")

        # Additional info
        ctk.CTkLabel(parent, text=f"Company: {company}", font=font).pack(anchor="center", padx=10, pady=(10, 0))
        ctk.CTkLabel(parent, text="Status: ✅ Active", font=font, text_color="#32cd32").pack(anchor="center", padx=10)

        # Clear button (already present, preserve styling)
        ctk.CTkButton(
            parent,
            text="🧹 Clear License Key",
            fg_color="#cc4b4b",
            hover_color="#aa2b2b",
            text_color="#ffffff",
            command=self.clear_license_and_exit
        ).pack(pady=(20, 0))

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

        # Update any active tooltip fonts
        for label, _ in self.active_tooltips:
            if label.winfo_exists():
                label.configure(font=(self.font_family, self.font_size))

        # Update PDF sessions
        for session in self.pdf_sessions.values():
            for widget in session.get("widgets_to_scale", []):
                try:
                    widget.configure(font=font)
                except Exception:
                    pass

            if "parts_frame" in session:
                self._apply_font_to_widget(session["parts_frame"], font)
            if hasattr(self, "update_log_view"):
                self.update_log_view()

        # Update other fixed tabs
        for tab in [self.settings_tab, self.keybinds_tab, self.about_tab]:
            for child in tab.winfo_children():
                self._apply_font_to_widget(child, font)

        # Update tab font sizes
        self._apply_tab_font_size()
    def _apply_tab_font_size(self):
        font = (self.font_family, self.font_size)

        # Main tabs (Logs, Settings, etc.)
        for child in self.notebook._segmented_button._buttons_dict.values():
            child.configure(font=font)

        # Splitter PDF tabs
        if hasattr(self, "pdf_tabview") and hasattr(self.pdf_tabview, "_segmented_button"):
            for child in self.pdf_tabview._segmented_button._buttons_dict.values():
                child.configure(font=font)
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
        confirm = messagebox.askyesno("Reset Form", "Are you sure you want to clear this form?")
        if not confirm:
            return

        tab = self.pdf_tabview.get()
        key = tab.replace(" ✖", "")  # Strip the ✖ symbol
        session = self.pdf_sessions.get(key)

        if not session:
            messagebox.showerror("Reset Error", "No active session to reset.")
            return

        for entry in session["entries"]:
            entry["revoked"].set(False)
            entry["agency"].set("")
            entry["description"].set("POA")
            entry["date"].set("")

        session["client_name_var"].set("")
        messagebox.showinfo("Form Reset", "This form has been cleared.")
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
    def add_tooltip(self, widget, text):
        tooltip = tk.Toplevel(widget)
        tooltip.withdraw()
        tooltip.overrideredirect(True)
        tooltip.config(bg="#333333")

        # Create the label using current font settings
        font = (self.font_family, self.font_size)
        label = tk.Label(
            tooltip,
            text=text,
            background="#333333",
            foreground="white",
            padx=6,
            pady=3,
            font=font,
            wraplength=240
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

        # 🧠 Optional: track for dynamic updates
        if not hasattr(self, "active_tooltips"):
            self.active_tooltips = []
        self.active_tooltips.append((label, tooltip))
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
                    for item in sessions:
                        path = item.get("file_path")
                        if path:
                            stem = Path(path).stem
                            label = f"{stem} ✖"
                            self.pdf_tabview.set(label)
                            self.update_idletasks()
                    # Return to first one
                    first_path = sessions[0].get("file_path")
                    if first_path:
                        stem = Path(first_path).stem
                        label = f"{stem} ✖"
                        self.pdf_tabview.set(label)
        except Exception as e:
            debug(f"Failed to auto-focus restored tabs: {e}", "error")
    def load_quick_split_pdf(self):
        paths = filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
        for path in paths:
            if path.lower().endswith(".pdf"):
                self.load_quick_split_pdf_from_path(path)
    def load_quick_split_pdf_from_path(self, path):
        try:
            reader = PdfReader(path)
            ranges = self.detect_split_ranges_from_reader(reader)

            out_folder = Path(self.settings.get("export_folder", "")) or Path.home() / "Desktop"
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            export_dir = out_folder / "Quick Split Files" / today_str
            export_dir.mkdir(parents=True, exist_ok=True)

            for i, r in enumerate(ranges, start=1):
                writer = PdfWriter()
                for p in range(r["start"], r["end"] + 1):
                    writer.add_page(reader.pages[p])

                original_name = re.sub(r'[\\/*?:"<>|]', "_", Path(path).stem)
                fname = f"{original_name} – Part {i:02d}.pdf"
                with open(export_dir / fname, "wb") as f:
                    writer.write(f)

            debug(f"{len(ranges)} files saved to: {export_dir}", "saved")
            messagebox.showinfo("Quick Split Complete", f"{len(ranges)} files saved to:\n{export_dir}")

        except Exception as e:
            debug(f"Failed to quick split: \n{e}", "error")
            messagebox.showerror("Error", f"Failed to quick split:\n{e}")
    def handle_quick_drop(self, event):
        raw = event.data.strip()
        paths = re.findall(r"\{(.*?)\}", raw)

        if not paths and raw.lower().endswith(".pdf"):
            paths = [raw]

        valid_pdfs = [p for p in paths if p.lower().endswith(".pdf")]

        if not valid_pdfs:
            messagebox.showerror("Invalid Drop", "Only PDF files are supported.")
            return

        for path in valid_pdfs:
            self.load_quick_split_pdf_from_path(path)
    def check_export_folder_prompt(self):
        current_folder = self.settings.get("export_folder", "")
        if not current_folder:
            answer = messagebox.askyesno("Set Export Folder?", "No default export folder is set.\nWould you like to choose one now?")
            if answer:
                self.set_export_folder()

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
    def handle_date_change(self, date_str):
        if len(date_str) != 6 or not date_str.isdigit():
            return  # not a full MMDDYY date yet
        self.check_future_date(date_str, callback_on_confirm=lambda: debug(f"Confirmed future date: {date_str}", "debug"))

    # ─── Log Management ───
    def load_full_log(self):
        if LOG_FILE.exists():
            with open(LOG_FILE, "r") as f:
                self.full_log_lines = f.readlines()
        else:
            self.full_log_lines = []

        self.update_log_view()
    def update_log_view(self, *args):

        font_body = (self.font_family, self.font_size)
        font_header = (self.font_family, self.font_size + 1, "bold")

        # Clear previous content
        for widget in self.log_scroll_frame.winfo_children():
            widget.destroy()

        query = self.search_var.get().lower()
        sort_mode = self.sort_mode_var.get()

        def extract_info(line):
            info = {"raw": line, "client": "", "date": ""}
            client_match = re.search(r"Client:\s*(.*?)\s*\|", line)
            date_match = re.match(r"\[(\d{4}-\d{2}-\d{2})", line)
            if client_match:
                info["client"] = client_match.group(1).strip()
            if date_match:
                info["date"] = date_match.group(1)
            return info

        parsed = [extract_info(l) for l in self.full_log_lines if "Client:" in l]

        if query:
            parsed = [p for p in parsed if query in p["raw"].lower()]

        reverse = sort_mode in ["Date ↓", "Z → A"]
        if "Date" in sort_mode:
            parsed.sort(key=lambda x: x["date"], reverse=reverse)
        else:
            parsed.sort(key=lambda x: x["client"].lower(), reverse=reverse)

        # Group by (date, client)
        grouped = {}
        for p in parsed:
            key = (p["date"], p["client"])
            grouped.setdefault(key, []).append(p["raw"])

        last_date = None
        for (date, client), lines in grouped.items():
            # Add date separator if needed
            if date != last_date:
                formatted = datetime.datetime.strptime(date, "%Y-%m-%d").strftime("──── %B %d, %Y ────")
                sep = ctk.CTkLabel(
                    self.log_scroll_frame,
                    text=formatted,
                    font=(self.font_family, self.font_size, "bold"),
                    text_color="#888888"
                )
                sep.pack(anchor="w", padx=12, pady=(10, 0))
                last_date = date

            # Bubble styling
            bubble_color = "#f8f4fa" if ctk.get_appearance_mode() == "Light" else "#2a2a2a"
            border_color = "#cccccc" if ctk.get_appearance_mode() == "Light" else "#444444"

            container = ctk.CTkFrame(
                self.log_scroll_frame,
                fg_color=bubble_color,
                border_color=border_color,
                border_width=1,
                corner_radius=12
            )
            container.pack(fill="x", padx=12, pady=6)

            title = f"{client} – {date}"
            ctk.CTkLabel(
                container,
                text=title,
                font=(self.font_family, self.font_size + 1, "bold"),
                anchor="w",
                padx=10,
                pady=6
            ).pack(fill="x")

            for line in lines:
                clean = re.sub(r"^\[.*?\]\s*", "", line.strip())

                tag_color = None
                if "Revoked: True" in clean:
                    tag_color = "#d86da0"
                elif "Skipped: [" in clean:
                    tag_color = "#cc4b4b"

                ctk.CTkLabel(
                    container,
                    text=clean,
                    anchor="w",
                    wraplength=820,
                    justify="left",
                    text_color=tag_color,
                    font=(self.font_family, self.font_size),
                    padx=12,
                    pady=4
                ).pack(fill="x", padx=4, pady=1)
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
    def open_log_export_popup(self):
        popup = tk.Toplevel(self)
        popup.title("Export Log")
        popup.geometry("460x520")
        popup.transient(self)
        popup.grab_set()
        popup.resizable(False, False)

        # Theme-aware
        appearance = ctk.get_appearance_mode()
        bg_color = "#ffffff" if appearance == "Light" else "#2e2e2e"
        popup.configure(bg=bg_color)

        font = (self.font_family, self.font_size)

        # ── Container: main frame with scroll and fixed footer ──
        main_frame = ctk.CTkFrame(popup)
        main_frame.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        scrollable = ctk.CTkScrollableFrame(main_frame, width=440, height=400)
        scrollable.pack(fill="both", expand=True)

        # Header
        ctk.CTkLabel(scrollable, text="Export Log Entries", font=(self.font_family, self.font_size + 2, "bold")).pack(pady=10)

        # ── Filters ──
        filters = {}

        def make_entry(label_text):
            ctk.CTkLabel(scrollable, text=label_text, font=font).pack(anchor="w")
            var = tk.StringVar()
            entry = ctk.CTkEntry(scrollable, textvariable=var)
            entry.pack(pady=2, fill="x")
            return var

        filters["client"] = make_entry("Client Name (partial ok)")
        filters["agency"] = make_entry("Agency Code (e.g., IRS, FTB)")
        filters["export_date"] = make_entry("Export Date (YYYY-MM-DD)")
        filters["part_date"] = make_entry("Part Date (MM-DD-YY)")

        ctk.CTkLabel(scrollable, text="Export Format", font=font).pack(pady=(10, 0))
        format_var = tk.StringVar(value="CSV")
        ctk.CTkOptionMenu(scrollable, values=["CSV", "TXT", "Print"], variable=format_var).pack()

        # ── Fixed Footer Buttons ──
        button_row = ctk.CTkFrame(popup)
        button_row.pack(pady=10)

        ctk.CTkButton(button_row, text="Export", command=lambda: (self.export_filtered_log(filters, format_var.get()), popup.destroy())).pack(side="left", padx=10)
        ctk.CTkButton(button_row, text="Cancel", command=popup.destroy).pack(side="left", padx=10)
    def export_filtered_log(self, filters, export_format):
        # Load all lines if not already loaded
        if not hasattr(self, "full_log_lines") or not self.full_log_lines:
            self.load_full_log()

        query_client = filters["client"].get().lower()
        query_agency = filters["agency"].get().lower()
        query_export_date = filters["export_date"].get()
        query_part_date = filters["part_date"].get()

        matches = []

        for line in self.full_log_lines:
            # Skip empty or malformed lines
            if not line.strip() or "Client:" not in line:
                continue

            client = self._extract_value(line, "Client").lower()
            agency = self._extract_value(line, "Agency").lower()
            part_date = self._extract_value(line, "Date")  # MM-DD-YY
            revoked = self._extract_value(line, "Revoked")
            desc = self._extract_value(line, "Desc")
            file = self._extract_value(line, "File")
            skipped = self._extract_value(line, "Skipped")
            pages = self._extract_value(line, "Pages")

            timestamp_match = re.match(r"\[(.*?)\]", line)
            export_date = timestamp_match.group(1).split()[0] if timestamp_match else ""

            # Apply filters
            if query_client and query_client not in client:
                continue
            if query_agency and query_agency not in agency:
                continue
            if query_export_date and query_export_date not in export_date:
                continue
            if query_part_date and query_part_date not in part_date:
                continue

            matches.append({
                "Export Date": export_date,
                "Client": client,
                "File": file,
                "Pages": pages,
                "Skipped": skipped,
                "Agency": agency,
                "Desc": desc,
                "Date": part_date,
                "Revoked": revoked
            })

        if not matches:
            messagebox.showinfo("No Matches", "No log entries matched your filters.")
            return

        if export_format == "CSV":
            file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
            if not file_path:
                return
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=matches[0].keys())
                writer.writeheader()
                writer.writerows(matches)
            messagebox.showinfo("Exported", f"{len(matches)} log entries saved to:\n{file_path}")

        elif export_format == "TXT":
            file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
            if not file_path:
                return
            with open(file_path, "w", encoding="utf-8") as f:
                for entry in matches:
                    f.write(" | ".join(f"{k}: {v}" for k, v in entry.items()) + "\n")
            messagebox.showinfo("Exported", f"{len(matches)} log entries saved to:\n{file_path}")

        elif export_format == "Print":
            # Write to temp file and open in browser for printing
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8")
            temp_file.write("<html><body><pre style='font-family:monospace'>\n")
            for entry in matches:
                temp_file.write(" | ".join(f"{k}: {v}" for k, v in entry.items()) + "\n")
            temp_file.write("</pre></body></html>")
            temp_file.close()
            webbrowser.open(f"file://{temp_file.name}")
    def _extract_value(self, line, label):
        match = re.search(fr"{label}:\s*([^|]+)", line)
        return match.group(1).strip() if match else ""

    # ─── PDF Load & Split ───
    def load_pdf(self):
        paths = filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
        for path in paths:
            if path.lower().endswith(".pdf"):
                self.load_pdf_from_path(path)
    def load_pdf_from_path(self, path, render=True):
        if not self.settings.get("tutorial_shown", False):
            self.start_tutorial()

        pdf_name = Path(path).stem

        # Prevent duplicate loads
        if pdf_name in self.pdf_sessions:
            messagebox.showinfo("Already Loaded", f"{pdf_name} is already open.")
            return

        try:
            reader = PdfReader(path)
            ranges = self.detect_split_ranges_from_reader(reader)

            # Create labeled tab with "✖"
            pdf_name = Path(path).stem
            tab_label = f"{pdf_name} ✖"
            tab = self.pdf_tabview.add(tab_label)
            self._apply_tab_font_size()
            self.pdf_tabview.set(tab_label)

            # Create and store session
            session = {
                "tab": tab,
                "tab_label": tab_label,
                "reader": reader,
                "path": Path(path),
                "ranges": ranges,
                "entries": [],
                "client_name_var": ctk.StringVar(),
                "last_exported_files": [],
                "widgets_to_scale": []
            }

            self.pdf_sessions[pdf_name] = session

            self.update_idletasks()  # Ensure UI is laid out before rendering
            self.render_splitter_tab(tab, session)

            self.enable_tab_closing()

        except Exception as e:
            messagebox.showerror("Error", str(e))
    def detect_split_ranges_from_reader(self, reader):
        debug("Starting detect_split_ranges", "debug")
        split_pages = []

        for idx, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            words = [w for w in re.findall(r"\S+", text) if w.strip()]
            uppercase = [w.upper() for w in words]
            debug(f"Page {idx+1}: {len(words)} words", "debug")

            if any("SPLIT" in w for w in uppercase) and ("HERE" in uppercase or len(words) <= 3):
                debug(f"→ SPLIT marker found on page {idx+1}", "debug")
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

        debug(f"Detected split ranges: {ranges}", "debug")
        return ranges
    def make_autofill_handler(self, field, var, index, entries_ref):
        prev_val = {"last": ""}

        def handler(*_):
            value = var.get()
            debug(f"Autofill triggered on part {index + 1} for '{field}' with value: '{value}'", "debug")

            for j in range(index + 1, len(entries_ref)):
                current_val = entries_ref[j][field].get()

                # Skip non-string comparisons (e.g., booleans)
                if not isinstance(value, str) or not isinstance(current_val, str):
                    debug(f" → Skipped Part {j + 1} '{field}' (non-string value)", "skipped")
                    continue

                if current_val == value[:-1]:
                    entries_ref[j][field].set(value)
                    debug(f" → Autofilled Part {j + 1} '{field}' with (forward): '{value}'", "debug")
                elif current_val == prev_val["last"]:
                    entries_ref[j][field].set(value)
                    debug(f" → Autofilled Part {j + 1} '{field}' with (backspace): '{value}'", "debug")
                else:
                    debug(f" → Skipped Part {j + 1} '{field}' (current = '{current_val}')", "debug")

            prev_val["last"] = value

        return handler
    def export_pdfs(self):
        raw_client = self.client_name_var.get()
        if not raw_client.strip():
            messagebox.showerror("Missing Client Name", "Please enter a client name.")
            return

        client_name = self.title_case(raw_client.strip())


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
        # Match any group enclosed in braces or fallback to single file
        raw = event.data.strip()
        paths = re.findall(r"\{(.*?)\}", raw)

        # If no curly braces found, assume it's a single path
        if not paths and raw.lower().endswith(".pdf"):
            paths = [raw]

        valid_files = [p for p in paths if p.lower().endswith(".pdf")]
        if not valid_files:
            messagebox.showerror("Invalid File(s)", "Only PDF files are supported.")
            return

        for path in valid_files:
            self.load_pdf_from_path(path)

        self.enable_tab_closing()
    def export_current_pdf(self):
        tab_name = self.pdf_tabview.get()
        session = self.pdf_sessions.get(tab_name)
        if session:
            self.export_pdf_session(session)
    def render_splitter_tab(self, tab_frame, session):
        for widget in tab_frame.winfo_children():
            widget.destroy()

        session["entries"] = []
        session["widgets_to_scale"] = []
        ranges = session["ranges"]

        # Outer content frame: form on the left, preview on the right
        content = ctk.CTkFrame(tab_frame)
        content.pack(fill="both", expand=True)

        # LEFT: Form area
        form_frame = ctk.CTkFrame(content)
        form_frame.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=(10, 5))

        # Client Name section
        client_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        client_frame.pack(pady=(10, 0), anchor="center")

        label = ctk.CTkLabel(client_frame, text="Client Name:")
        label.grid(row=0, column=0)
        debug("Adding the enchance", "debug")
        self.enhance_all_entries()
        session["widgets_to_scale"].append(label)

        info_icon = ctk.CTkLabel(client_frame, text="❓", text_color="#888888", cursor="question_arrow")
        info_icon.grid(row=0, column=1, padx=(5, 10))
        self.add_tooltip(info_icon,
                         "TitleCase Rules:\n"
                         "• Words are capitalized automatically\n"
                         "• Acronyms like LLC, INC, IRS stay uppercase\n"
                         "• INC. is preserved with period\n"
                         "• ALL CAPS input stays all caps"
                         )
        session["widgets_to_scale"].append(info_icon)

        entry = ctk.CTkEntry(client_frame, textvariable=session["client_name_var"], width=300)
        entry.grid(row=0, column=2)
        session["widgets_to_scale"].append(entry)

        # Parts section
        for idx, r in enumerate(ranges, start=1):
            part_frame = ctk.CTkFrame(form_frame, fg_color="transparent", width=700)
            part_frame.pack(pady=6, anchor="center")
            part_frame.pack_propagate(False)

            part_label = ctk.CTkLabel(part_frame, text=f"Part {idx} — Pages {r['start']+1} to {r['end']+1}")
            part_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
            session["widgets_to_scale"].append(part_label)

            revoked_var = ctk.BooleanVar()
            agency_var = ctk.StringVar()
            desc_var = ctk.StringVar(value="POA")
            date_var = ctk.StringVar()

            switch = ctk.CTkSwitch(part_frame, text="Revoked", variable=revoked_var)
            switch.grid(row=1, column=0, sticky="w", pady=2)
            session["widgets_to_scale"].append(switch)

            agency_label = ctk.CTkLabel(part_frame, text="Agency Code:")
            agency_label.grid(row=2, column=0, sticky="w", pady=2)
            self.add_tooltip(agency_label, "I = IRS, F = FTB, E = EDD, C = CDTFA, B = BOE")
            session["widgets_to_scale"].append(agency_label)

            agency_entry = ctk.CTkEntry(part_frame, textvariable=agency_var)
            agency_entry.grid(row=2, column=1, padx=(10, 0), pady=2)
            session["widgets_to_scale"].append(agency_entry)

            desc_frame = ctk.CTkFrame(part_frame, fg_color="transparent")
            desc_frame.grid(row=3, column=0, sticky="w", columnspan=2)

            desc_label = ctk.CTkLabel(desc_frame, text="Description:")
            desc_label.pack(side="left")
            session["widgets_to_scale"].append(desc_label)

            desc_info = ctk.CTkLabel(desc_frame, text="❓", text_color="#888888", cursor="question_arrow")
            desc_info.pack(side="left", padx=(5, 0))
            self.add_tooltip(desc_info,
                             "TitleCase Rules:\n"
                             "• Words are capitalized automatically\n"
                             "• Acronyms like LLC, INC, IRS stay uppercase\n"
                             "• INC. is preserved with period\n"
                             "• ALL CAPS input stays all caps"
                             )
            session["widgets_to_scale"].append(desc_info)

            desc_entry = ctk.CTkEntry(part_frame, textvariable=desc_var)
            desc_entry.grid(row=3, column=1, padx=(10, 0), pady=2)
            session["widgets_to_scale"].append(desc_entry)

            date_label = ctk.CTkLabel(part_frame, text="Date (MMDDYY):")
            date_label.grid(row=4, column=0, sticky="w", pady=2)
            session["widgets_to_scale"].append(date_label)

            date_entry = ctk.CTkEntry(part_frame, textvariable=date_var)
            date_entry.grid(row=4, column=1, padx=(10, 0), pady=2)
            session["widgets_to_scale"].append(date_entry)

            session["entries"].append({
                "range": r,
                "revoked": revoked_var,
                "agency": agency_var,
                "description": desc_var,
                "date": date_var
            })

            # Autofill setup
            agency_var.trace_add("write", self.make_autofill_handler("agency", agency_var, idx - 1, session["entries"]))
            desc_var.trace_add("write", self.make_autofill_handler("description", desc_var, idx - 1, session["entries"]))
            date_var.trace_add("write", self.make_autofill_handler("date", date_var, idx - 1, session["entries"]))
            revoked_var.trace_add("write", self.make_autofill_handler("revoked", revoked_var, idx - 1, session["entries"]))

            self.enhance_entry_keybinds(entry)
            self.enhance_entry_keybinds(agency_entry)
            self.enhance_entry_keybinds(desc_entry)
            self.enhance_entry_keybinds(date_entry)


# RIGHT: PDF preview area
        preview_frame = ctk.CTkFrame(content, width=600)
        preview_frame.pack_propagate(False)
        preview_frame.pack(side="left", fill="y", padx=10, pady=10)

        self.render_pdf_preview(session, preview_frame)

        # "Make Client Folder" checkbox
        make_folder_checkbox = ctk.CTkCheckBox(
            tab_frame,
            text="Make Client Folder",
            variable=self.make_client_folder_var
        )
        make_folder_checkbox.pack(pady=(10, 0))
        session["widgets_to_scale"].append(make_folder_checkbox)

        # Bottom buttons
        button_row = ctk.CTkFrame(tab_frame, fg_color="transparent")
        button_row.pack(pady=10)

        export_btn = ctk.CTkButton(button_row, text="Export PDFs", command=lambda: self.export_session(session))
        export_btn.pack(side="left", padx=10)
        session["widgets_to_scale"].append(export_btn)

        reset_btn = ctk.CTkButton(button_row, text="Reset Form", fg_color="#cc4b4b", hover_color="#aa2b2b",
                                  command=self.reset_ui)
        reset_btn.pack(side="left", padx=10)
        session["widgets_to_scale"].append(reset_btn)

        keybind_btn = ctk.CTkButton(button_row, text="Show Keybinds", command=self.open_keybind_overlay)
        keybind_btn.pack(side="left", padx=10)
        session["widgets_to_scale"].append(keybind_btn)
        self._apply_font_size()
    def render_pdf_preview(self, session, frame, page_index=0):
        try:
            doc = fitz.open(str(session["path"]))
            page_count = doc.page_count
            page_index = max(0, min(page_index, page_count - 1))
            page = doc.load_page(page_index)

            debug(f"Rendering page {page_index + 1} of {page_count} for preview", "debug")

            # Scale the page
            zoom = 2
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Resize to fit preview panel
            max_width = 440
            max_height = 800
            aspect_ratio = pix.height / pix.width
            target_width = max_width
            target_height = int(target_width * aspect_ratio)

            if target_height > max_height:
                target_height = max_height
                target_width = int(target_height / aspect_ratio)

            img = img.resize((target_width, target_height), Image.LANCZOS)

            # Create image for display
            ctk_image = CTkImage(light_image=img, dark_image=img, size=(target_width, target_height))

            # Store preview state
            session["preview_page_index"] = page_index
            session["preview_frame"] = frame
            session["preview_page_count"] = page_count

            # === Controls ===
            control_frame = ctk.CTkFrame(frame, fg_color="transparent")
            control_frame.pack(pady=(10, 0))

            if page_index > 0:
                prev_btn = ctk.CTkButton(
                    control_frame, text="← Prev", width=80,
                    command=lambda: self.update_pdf_preview_page(session, -1)
                )
                prev_btn.pack(side="left", padx=5)

            zoom_btn = ctk.CTkButton(
                control_frame, text="🔍 Zoom", width=100,
                command=lambda: self.open_fullscreen_preview(session, page_index)
            )
            zoom_btn.pack(side="left", padx=5)

            if page_index < page_count - 1:
                next_btn = ctk.CTkButton(
                    control_frame, text="Next →", width=80,
                    command=lambda: self.update_pdf_preview_page(session, 1)
                )
                next_btn.pack(side="left", padx=5)

            # === Image Preview ===
            img_label = ctk.CTkLabel(frame, image=ctk_image, text="")
            img_label.image = ctk_image
            img_label.pack(pady=(10, 5))

            # === Page number label ===
            page_label = ctk.CTkLabel(frame, text=f"Page {page_index + 1} of {page_count}")
            page_label.pack(pady=(0, 10))
            session["preview_page_label"] = page_label

            doc.close()

        except Exception as e:
            debug(f"Failed to render PDF preview (page {page_index}): {e}", "debug")
            ctk.CTkLabel(frame, text="Unable to preview PDF").pack()
    def export_session(self, session):
        client_name = self.title_case(session["client_name_var"].get().strip())
        if not client_name:
            messagebox.showerror("Missing Client Name", "Please enter a client name.")
            return

        # 🧠 Check for future dates BEFORE proceeding
        for idx, entry in enumerate(session["entries"], start=1):
            date_str = entry["date"].get()
            if not re.fullmatch(r"\d{6}", date_str):
                continue  # skip incomplete

            try:
                today = datetime.date.today()
                entered_date = datetime.datetime.strptime(date_str, "%m%d%y").date()
                if entered_date > today and not self.settings.get("suppressFutureDateWarning", False):
                    debug(f"Future date found in part {idx}: {date_str}", "debug")
                    self.check_future_date(date_str, callback_on_confirm=lambda: self._finalize_export(session))
                    return  # Wait for user confirmation
            except Exception:
                continue  # invalid date format – will raise later in format_date

        self._finalize_export(session)
    def _finalize_export(self, session):
        debug("Finalizing export...", "debug")

        client_name = self.title_case(session["client_name_var"].get().strip())
        folder = self.settings.get("export_folder")

        if not folder:
            folder = filedialog.askdirectory(title="Select Export Folder")
            if not folder:
                return

        if self.make_client_folder_var.get():
            out_dir = Path(folder) / client_name
        else:
            out_dir = Path(folder)

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

        # Logging
        if self.settings.get("export_log_enabled", True):
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                for line in log_lines:
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"[{timestamp}] {line}\n")
            self.load_full_log()

        messagebox.showinfo("Export Complete", f"Exported to: {out_dir}")

        tab_name = next((name for name, s in self.pdf_sessions.items() if s is session), None)
        if tab_name:
            tab_label = session.get("tab_label", tab_name)
            self.pdf_tabview.delete(tab_label)
            self.pdf_sessions.pop(tab_name, None)
    def split_paths(self, data):
        # Example: '{C:/file1.pdf} {C:/file2.pdf}'
        return [p.strip("{}") for p in data.strip().split() if p.strip()]
    def add_plus_tab(self):
        if not hasattr(self, "pdf_tabview") or not isinstance(self.pdf_tabview, ctk.CTkTabview):
            return

        existing_tabs = getattr(self.pdf_tabview, "_tabs", {})
        if "+" in existing_tabs:
            return

        plus_tab = self.pdf_tabview.add("+")
        self.pdf_tabview.set("+")  # Focus on the plus tab

        plus_frame = ctk.CTkFrame(plus_tab)
        plus_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # 🆕 Use dynamic font settings
        font = (self.font_family, self.font_size)

        label1 = ctk.CTkLabel(plus_frame, text="Click below to open a new PDF", font=font)
        label1.pack(pady=20)

        open_btn = ctk.CTkButton(plus_frame, text="➕ Open PDF", command=self.load_pdf, font=font)
        open_btn.pack()

        label2 = ctk.CTkLabel(plus_frame, text="Or drag and drop files into this area", font=font)
        label2.pack(pady=(10, 0))
    def download_split_here_sheet(self):
        url = "https://raw.githubusercontent.com/shhmethan/CleanCutPDF/master1/FullApp/resources/split_here_background.pdf"

        out_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")],
            title="Save SPLIT HERE Sheet As",
            initialfile="split_here_sheet.pdf"
        )
        if not out_path:
            return

        try:
            with urllib.request.urlopen(url) as response:
                pdf_bytes = response.read()

            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            page = doc[0]

            # Insert text
            page.insert_text(
                (72, 72),
                "SPLIT HERE",
                fontsize=36,
                color=(0, 0, 0),
                fontname="helv"
            )

            doc.save(out_path)
            doc.close()
            messagebox.showinfo("Saved", f"SPLIT HERE sheet saved to:\n{out_path}")
            debug(f"Saved SPLIT HERE sheet to: {out_path}", "debug")
        except Exception as e:
            messagebox.showerror("Error", f"Could not generate template:\n{e}")
            debug(f"Failed to generate SPLIT HERE sheet: {e}", "error")

    # ─── PDF Preview ───
    def update_pdf_preview_page(self, session, offset):
        import fitz

        try:
            doc = fitz.open(str(session["path"]))
            max_page = doc.page_count
            current = session.get("preview_page_index", 0)
            new_page = max(0, min(current + offset, max_page - 1))
            doc.close()

            debug(f"Navigating from page {current + 1} to page {new_page + 1}", "debug")

            for widget in session["preview_frame"].winfo_children():
                widget.destroy()

            self.render_pdf_preview(session, session["preview_frame"], page_index=new_page)

        except Exception as e:
            debug(f"Failed to update preview page: {e}", "error")
    def update_pdf_preview_page(self, session, offset):
        try:
            doc = fitz.open(str(session["path"]))
            page_count = doc.page_count
            current = session.get("preview_page_index", 0)
            new_page = max(0, min(current + offset, page_count - 1))
            doc.close()

            debug(f"Navigating from page {current + 1} to page {new_page + 1}", "debug")

            for widget in session["preview_frame"].winfo_children():
                widget.destroy()

            self.render_pdf_preview(session, session["preview_frame"], page_index=new_page)

        except Exception as e:
            debug(f"Failed to update preview page: {e}", "error")
    def open_fullscreen_preview(self, session, page_index=0):
        debug(f"Opening fullscreen preview for page {page_index + 1}", "debug")

        zoom_state = {"scale": 1.0}  # temp default

        win = tk.Toplevel(self)
        win.title(f"Zoomed Page {page_index + 1}")
        win.configure(bg="#dddddd")
        win.state("zoomed")

        canvas = tk.Canvas(win, bg="#dddddd", highlightthickness=0)
        canvas.pack(fill="both", expand=True, side="left")

        h_scroll = tk.Scrollbar(win, orient="horizontal", command=canvas.xview)
        h_scroll.pack(side="bottom", fill="x")
        v_scroll = tk.Scrollbar(win, orient="vertical", command=canvas.yview)
        v_scroll.pack(side="right", fill="y")

        canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)

        def render_scaled_image():
            try:
                doc = fitz.open(str(session["path"]))
                page = doc.load_page(page_index)

                mat = fitz.Matrix(zoom_state["scale"], zoom_state["scale"])
                pix = page.get_pixmap(matrix=mat)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                photo = ImageTk.PhotoImage(img)

                canvas.delete("all")
                canvas.image = photo
                canvas.update_idletasks()

                cw = canvas.winfo_width()
                ch = canvas.winfo_height()
                img_x = (cw - pix.width) // 2 if pix.width < cw else 0
                img_y = (ch - pix.height) // 2 if pix.height < ch else 0

                canvas.create_image(img_x, img_y, image=photo, anchor="nw")
                canvas.config(scrollregion=(0, 0, pix.width, pix.height))
                debug(f"Rendered {pix.width}x{pix.height} at center ({img_x}, {img_y})", "debug")

                doc.close()
            except Exception as e:
                debug(f"Failed to render zoomed image: {e}", "error")
                tk.messagebox.showerror("Render Error", str(e))

        def _on_mousewheel(event):
            if event.state & 0x0004:  # Ctrl held
                delta = 1 if event.delta > 0 else -1
                new_zoom = max(0.5, min(5.0, zoom_state["scale"] + 0.25 * delta))
                if new_zoom != zoom_state["scale"]:
                    zoom_state["scale"] = new_zoom
                    debug(f"Ctrl+Scroll → zoom to {new_zoom:.2f}", "debug")
                    render_scaled_image()
            else:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                debug(f"MouseWheel scroll: delta={event.delta}", "debug")

        def _on_shiftwheel(event):
            canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
            debug(f"Shift+Wheel scroll (horizontal): delta={event.delta}", "debug")

        def close_on_escape(event):
            debug("ESC pressed — closing fullscreen preview", "debug")
            win.destroy()

        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind_all("<Shift-MouseWheel>", _on_shiftwheel)
        win.bind("<Escape>", close_on_escape)

        # Compute fit-to-width zoom after layout
        def set_initial_zoom():
            doc = fitz.open(str(session["path"]))
            page = doc.load_page(page_index)
            page_width = page.rect.width
            canvas_width = canvas.winfo_width()

            if canvas_width <= 1:  # Not ready yet
                debug("Canvas not ready — retrying zoom calc...", "debug")
                win.after(50, set_initial_zoom)
                return

            fit_zoom = max(1.0, min(5.0, canvas_width / page_width))
            zoom_state["scale"] = round(fit_zoom, 2)
            debug(f"Calculated initial zoom to fit width: {zoom_state['scale']:.2f}", "debug")
            render_scaled_image()
            doc.close()

        win.after(50, set_initial_zoom)  # Wait for layout before rendering

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
        debug("Title case start", "debug")
        acronyms = ACRONYMS

        def smart_capitalize(word):
            if not word:
                return ""
            if word.upper() in acronyms:
                return word.upper()
            if '-' in word:
                return '-'.join(smart_capitalize(part) for part in word.split('-'))
            if word.lower().startswith("mc") and len(word) > 2:
                return "Mc" + word[2].upper() + word[3:].lower()
            if word.lower().startswith("mac") and len(word) > 3:
                return "Mac" + word[3].upper() + word[4:].lower()
            if word.lower().startswith("o'") and len(word) > 2:
                return "O'" + word[2].upper() + word[3:].lower()
            if any(c.isupper() for c in word[1:]):  # preserve mixed caps
                return word
            return word[0].upper() + word[1:].lower()

        if not s.strip():
            return ""

        words = re.findall(r'\S+', s)
        temp = ' '.join(smart_capitalize(w) for w in words)
        debug(f" TC --> {temp}", "debug")
        return temp

    # ─── Keybinds ───
    def focus_search(self):
        debug("Focusing search bar", "debug")
        self.notebook.set("Logs")
        self.search_entry.focus_set()
    def save_keybinds(self):
        self.keybindings = {action: var.get() for action, var in self.keybind_vars.items()}
        debug(f"Saving keybindings: {self.keybindings}", "debug")
        with open(KEYBINDS_FILE, "w") as f:
            json.dump(self.keybindings, f, indent=2)
        debug("Keybinds written to file", "debug")
        self.apply_keybinds()
        messagebox.showinfo("Keybinds Updated", "New keybindings have been saved.")
    def apply_keybinds(self):
        debug("Applying keybinds:", "debug")

        try:
            keyboard.unhook_all_hotkeys()
        except AttributeError as e:
            debug(f"Skipped unhook_all_hotkeys due to: {e}", "skip")

        for action, combo in self.keybindings.items():
            debug(f"{action} → {combo}", "bind")

            callback = self.get_action_callback(action)
            try:
                keyboard.add_hotkey(combo, lambda a=action, cb=callback: self._run_if_focused(a, cb))
                debug(f"Keybind added: {combo}", "keybind")
            except ValueError as e:
                debug(f"Failed to bind {combo}: {e}", "error")

        keyboard.add_hotkey("ctrl+alt+d", self.open_debug_console)
    def undo_last_export(self):
        debug("Undo keybind triggered", "debug")
        debug(f"Files pending undo: {self.last_exported_files}", "debug")

        if not self.last_exported_files:
            messagebox.showinfo("Undo", "No export to undo.")
            return

        confirm = messagebox.askyesno(
            title="Confirm Undo",
            message="Are you sure you want to permanently delete the most recent export?\n\nThis cannot be undone."
        )

        if not confirm:
            debug("Undo canceled by user", "debug")
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
                debug(f"Failed to delete {path}: {e}", "debug")

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(LOG_FILE, "a", encoding="utf-8") as f:
            if deleted > 0:
                for path in self.last_exported_files:
                    f.write(f"[{timestamp}] Undo: Deleted '{path.name}' from '{path.parent}'\n")
                debug(f"Undo complete: {deleted} file(s) deleted", "debug")
                self.last_exported_files = []
            else:
                f.write(f"[{timestamp}] Undo attempted, but no files were deleted.\n")
                debug("Undo attempted, but no files were deleted.", "debug")

        self.load_full_log()
    def _debug_keybind(self, action_name, callback):
        if self.setting_keybind:
            debug(f"Ignored keybind '{action_name}' while setting new key", "debug")
            return
        debug(f"Keybind triggered: {action_name}", "debug")
        callback()
    def start_keybind_input(self, action, label_widget):
        debug(f"Starting keybind input for: {action}", "debug")
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
                    debug(f"Captured keybind for {action}: {combo}", "debug")
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
                debug(f"Temporarily unbound: <{combo}>", "debug")
            except Exception as e:
                debug(f"Failed to unbind <{combo}>: {e}", "debug")
    def enable_tab_closing(self):
        # Must delay until widgets exist
        self.after(100, self._bind_tab_close_events)
    def _bind_tab_close_events(self):
        try:
            for name, button in self.pdf_tabview._segmented_button._buttons_dict.items():
                button.unbind("<Button-1>")
                button.bind("<Button-1>", lambda e, tab=name: self._on_tab_left_click(e, tab))
                debug(f"Bound left-click to tab: {name}", "debug")
        except Exception as e:
            debug(f"Failed to bind tab click events: {e}", "debug")
    def _on_tab_left_click(self, event, tab_label):
        if tab_label == "+":
            debug(f"Clicked '+' tab — ignoring", "debug")
            return

        widget = event.widget
        click_x = event.x
        width = widget.winfo_width()

        debug(f"Clicked tab '{tab_label}' at x={click_x} of width={width}", "debug")

        # Determine if click was on the '✖'
        if tab_label.endswith("✖") and click_x > width - 25:
            base_name = tab_label.replace(" ✖", "")
            debug(f"Detected ✖ click on '{tab_label}' → base name: '{base_name}'", "debug")

            confirm = messagebox.askyesno("Close Tab", f"Close '{base_name}'?")
            if confirm:
                debug(f"Closing tab '{tab_label}' and deleting session '{base_name}'", "debug")

                self.pdf_tabview.delete(tab_label)

                if base_name in self.pdf_sessions:
                    del self.pdf_sessions[base_name]
                    debug(f"Session '{base_name}' removed from pdf_sessions", "debug")
                    self.save_sessions()
                else:
                    debug(f"[DEBUG] No matching session found for '{base_name}'")
            else:
                debug(f"[DEBUG] User canceled close for '{tab_label}'")
        else:
            debug(f"Click not in ✖ zone for '{tab_label}' — tab selected", "debug")
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
            debug(f"New Text: {new_before}", "debug")
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
            debug(f"New Text: {new_after}", "debug")
            entry_widget.delete(0, "end")
            entry_widget.insert(0, before + new_after)
            entry_widget.icursor(len(before))
            return "break"

        entry_widget.bind("<Control-BackSpace>", delete_word_left)
        entry_widget.bind("<Control-Delete>", delete_word_right)
    def open_keybind_overlay(self):
        if hasattr(self, "keybind_overlay") and self.keybind_overlay.winfo_exists():
            self.keybind_overlay.lift()
            return

        self.keybind_overlay = tk.Toplevel(self)
        self.keybind_overlay.title("Keybinds")
        self.keybind_overlay.attributes("-topmost", True)
        self.keybind_overlay.resizable(False, False)

        appearance = ctk.get_appearance_mode()
        bg_color = "#ffffff" if appearance == "Light" else "#2e2e2e"
        fg_color = "#000000" if appearance == "Light" else "#ffffff"

        self.keybind_overlay.configure(bg=bg_color)

        frame = tk.Frame(self.keybind_overlay, bg=bg_color)
        frame.pack(padx=12, pady=12)

        tk.Label(frame, text="Keyboard Shortcuts", font=(self.font_family, self.font_size + 2, "bold"),
                 bg=bg_color, fg=fg_color).pack(anchor="w", pady=(0, 10))

        for action, combo in self.keybindings.items():
            tk.Label(frame, text=f"{combo:<15} — {action}", anchor="w",
                     font=(self.font_family, self.font_size),
                     bg=bg_color, fg=fg_color).pack(anchor="w")

        tk.Button(frame, text="Close", command=self.keybind_overlay.destroy).pack(pady=(10, 0))
    def _handle_ctrl_shift_v(self, event):
        try:
            clipboard_text = self.clipboard_get()
        except tk.TclError:
            return

        widget = self.focus_get()
        if isinstance(widget, (tk.Entry, ctk.CTkEntry, tk.Text)):
            try:
                widget.insert("insert", clipboard_text)
            except Exception as e:
                debug(f"[DEBUG] Paste failed: {e}")
    def paste_clipboard(self):
        try:
            clipboard_text = self.clipboard_get()
        except tk.TclError:
            debug("[DEBUG] Clipboard is empty or unreadable")
            return

        target = self.focus_get()
        debug(f"[DEBUG] Attempting to paste into: {target} ({type(target)})")

        try:
            if isinstance(target, (ctk.CTkEntry, tk.Entry)):
                if str(target.cget("state")) != "disabled":
                    current = target.get()
                    pos = target.index("insert")
                    target.delete(0, "end")
                    new_text = current[:pos] + clipboard_text + current[pos:]
                    target.insert(0, new_text)
                    target.icursor(pos + len(clipboard_text))
                else:
                    debug("[DEBUG] Entry widget is disabled — skipping paste")
            elif isinstance(target, (ctk.CTkTextbox, tk.Text)):
                target.insert("insert", clipboard_text)
            else:
                debug("[DEBUG] Focused widget does not support paste")
        except Exception as e:
            debug(f"[DEBUG] Paste failed: {e}")
    def enhance_all_entries(self):
        def bind_text_nav(entry_widget):
            def delete_word_left(event):
                pos = entry_widget.index("insert")
                text = entry_widget.get()
                debug(f"[Keybind] Ctrl+Backspace pressed at pos {pos} with text: '{text}'", "debug")
                before = text[:pos]
                after = text[pos:]
                new_before = re.sub(r'\s*\S+\s*$', '', before)
                debug(f"[Keybind] Before deletion: '{before}' → After: '{new_before}'", "debug")
                entry_widget.delete(0, "end")
                entry_widget.insert(0, new_before + after)
                entry_widget.icursor(len(new_before))
                return "break"

            def delete_word_right(event):
                pos = entry_widget.index("insert")
                text = entry_widget.get()
                debug(f"[Keybind] Ctrl+Delete pressed at pos {pos} with text: '{text}'", "debug")
                before = text[:pos]
                after = text[pos:]
                new_after = re.sub(r'^\s*\S+\s*', '', after)
                debug(f"[Keybind] After deletion: '{after}' → Remaining: '{new_after}'", "debug")
                entry_widget.delete(0, "end")
                entry_widget.insert(0, before + new_after)
                entry_widget.icursor(len(before))
                return "break"

            entry_widget.bind("<Control-BackSpace>", delete_word_left)
            entry_widget.bind("<Control-Delete>", delete_word_right)
            entry_widget.bind("<Control-Left>", lambda e: entry_widget.icursor(entry_widget.index("insert") - len(re.findall(r'\S+', entry_widget.get()[:entry_widget.index("insert")]))[-1]))
            entry_widget.bind("<Control-Right>", lambda e: entry_widget.icursor(entry_widget.index("insert") + len(re.findall(r'\S+', entry_widget.get()[entry_widget.index("insert"):]))[0]))

    # Walk through all widgets and bind if it's an entry
        for widget in self.winfo_children():
            self._bind_recursive(widget, bind_text_nav)
    def _bind_recursive(self, widget, handler_fn):
        for child in widget.winfo_children():
            if isinstance(child, (tk.Entry, ctk.CTkEntry)):
                handler_fn(child)
            self._bind_recursive(child, handler_fn)
    def _run_if_focused(self, action, callback):
        if self.focus_displayof() is not None:
            debug(f"{action} triggered while focused", "keybind")
            callback()
        else:
            debug(f"{action} ignored (window not focused)", "keybind")

    # ─── Debug Window ───
    def open_debug_console(self):
        if self.debug_console_window and self.debug_console_window.winfo_exists():
            self.debug_console_window.lift()
            return

        self.debug_console_window = tk.Toplevel(self)
        self.debug_console_window.title(f"CleanCutPDF v{CURRENT_VERSION}")
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
            bg_color = "#fdf0f5" if self.theme == "Light Pink" else "#ffffff"
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
             "This tutorial will guide you through the core features of the app.\n\nClick OK to begin.",
             "Splitter"),

            ("Splitter Tab",
             "This is where you drag and drop PDFs or click ➕ to load them.\nSplit markers like 'SPLIT HERE' are detected automatically.",
             "Splitter"),

            ("Editing Parts",
             "Each split part has fields like Revoked, Agency, Description, and Date.\nThese are used to generate the final filenames.",
             "Splitter"),

            ("Client Name",
             "Enter the client name for the current file.\nYou can toggle whether a folder is created per client with the checkbox above the Export button.",
             "Splitter"),

            ("Keyboard Shortcuts",
             "Click 'Show Keybinds' to see shortcuts while working.\nYou can also view or customize keybinds in the Keybinds tab.",
             "Splitter"),

            ("Exporting",
             "Click 'Export PDFs' to generate files.\nYou'll be prompted if you enter a future date. A folder will be created automatically unless you uncheck the box.",
             "Splitter"),

            ("Quick Split Tab",
             "Use this for fast splitting — no metadata required.\nIt generates files named like 'Part 1 – OriginalFile.pdf'.",
             "QuickSplitter"),

            ("Settings Tab",
             "This tab is now organized into sections on the left.\nLet’s walk through them quickly.",
             "Settings"),

            ("Appearance Settings",
             "Change theme, font size, and font family here.",
             "Settings",
             lambda: self._show_settings_section("Appearance")),

            ("Export Settings",
             "Choose your default export folder, and toggle export log generation here.",
             "Settings",
             lambda: self._show_settings_section("Export")),

            ("Behavior Settings",
             "Enable blank-page removal and automatic session restore.",
             "Settings",
             lambda: self._show_settings_section("Behavior")),

            ("License Settings",
             "View or clear your license info here.",
             "Settings",
             lambda: self._show_settings_section("License")),

            ("Logs Tab",
             "Search, sort, and filter all past exports.\nLogs are now grouped by file and date for clarity.",
             "Logs"),

            ("Keybinds Tab",
             "Customize all app keybindings here.\nThe layout has been updated to be more readable and uniform.",
             "Keybinds"),

            ("You're Ready!",
             "That’s it! You can revisit this tutorial anytime via Settings.\n\nHappy splitting!",
             "Splitter")
        ]

        def show_step(index):
            if index >= len(steps):
                self.settings["tutorial_shown"] = True
                self.save_settings()
                return

            title, msg, tab = steps[index][:3]
            callback = steps[index][3] if len(steps[index]) > 3 else None

            self.notebook.set(tab)
            if callback:
                callback()

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
        self.hide_loading_overlay()

        def hash_key(key):
            return hashlib.sha256(key.encode("utf-8")).hexdigest()

        debug("Starting license check...", "debug")

        # Step 1: Check for saved license file
        if LICENSE_FILE.exists():
            debug(f"Found local license file at: {LICENSE_FILE}", "debug")
            try:
                with open(LICENSE_FILE, "r") as f:
                    saved = json.load(f)
                license_key = saved.get("license_key", "").strip()
                debug(f"Loaded cached license key: {license_key}", "debug")
            except Exception as e:
                messagebox.showerror("License Error", f"Failed to read license file:\n{e}")
                debug(f"Failed to load license file: {e}", "debug")
                return False
        else:
            debug("No license file found, prompting for key...", "debug")
            license_key = tk.simpledialog.askstring(
                "License Required", "Enter your CleanCutPDF license key:"
            )
            if not license_key:
                messagebox.showerror("License Required", "A license key is required to use this app.")
                debug("License entry cancelled or empty.", "debug")
                return False
            license_key = license_key.strip()

        # Step 2: Hash the entered key
        hashed_key = hash_key(license_key)
        debug(f"SHA-256 hash of entered key: {hashed_key}", "debug")

        # Step 3: Fetch the remote license list
        try:
            url = "https://raw.githubusercontent.com/shhmethan/CleanCutPDF/refs/heads/master1/licenses.json"
            debug(f"Fetching license data from: {url}", "debug")
            context = ssl._create_unverified_context()
            with urllib.request.urlopen(url, context=context) as response:
                data = json.loads(response.read())
            debug("Successfully fetched license list.", "debug")
        except Exception as e:
            messagebox.showerror("Network Error", f"Could not check license:\n{e}")
            debug(f"Failed to fetch license list: {e}", "debug")
            return False

        # Step 4: Validate hash
        valid_licenses = data.get("licenses", {})
        info = valid_licenses.get(hashed_key)

        if info:
            company = info.get("company", "Unknown Organization")
            debug(f"License key is valid! Company: {company}", "debug")

            # Save the license locally
            with open(LICENSE_FILE, "w") as f:
                json.dump({"license_key": license_key, "company": company}, f, indent=2)
            debug("License saved locally.", "debug")

            self.licensed_company = company
            self.title(f"CleanCutPDF – Licensed to {company}")
            return True
        else:
            messagebox.showerror("Invalid License", "The entered license key is not valid.")
            debug("No match found for hashed key. License is invalid.", "debug")
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