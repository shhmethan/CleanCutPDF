# ─── Standard Library ────────────────────────────────────────────────
import datetime
import copy
import hashlib
import io
import json
import re
import ssl
import sys
import urllib.request
import csv
import webbrowser
from pathlib import Path
import shutil
import tempfile
import os
import time
import subprocess

# ─── Third-Party Libraries ───────────────────────────────────────────
import pymupdf as fitz
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
CURRENT_VERSION = "1.8.0"
VERSION_URL = "https://raw.githubusercontent.com/shhmethan/CleanCutPDF/refs/heads/master1/version.json"

BASE_DIR = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).parent
USER_DATA_DIR = Path.home() / ".cleancutpdf"
APP_ICON = BASE_DIR / "resources" / "favicon.ico"

USER_DATA_DIR.mkdir(exist_ok=True)
SETTINGS_FILE = USER_DATA_DIR / "settings.json"
LOG_FILE = USER_DATA_DIR / "full.log"
DEBUG_FILE = USER_DATA_DIR / "debug.log"
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
WORKSPACES = {
    "Accounting": {
        "client_label": "Client Name",
        "summary": "Accounting and tax-document workflow with agency, revoked status, description, and date.",
        "default_filename_template": "{client}_{revoked}_{agency_description}_{date}",
        "fields": [
            {
                "key": "revoked", "label": "Revoked", "type": "bool", "placement": "header",
                "default": False, "autofill": True
            },
            {
                "key": "agency", "label": "Agency Code", "type": "text", "placeholder": "F",
                "default": "", "autofill": True,
                "tooltip": "Agency Codes:\n• I = IRS\n• F = FTB\n• E = EDD\n• C = CDTFA\n• B = BOE"
            },
            {
                "key": "description", "label": "Description", "type": "text", "placeholder": "POA",
                "default": "POA", "autofill": True, "title_case": True,
                "tooltip": "The default Description and its forward-autofill behavior are customizable per workspace in Settings > Workspaces."
            },
            {
                "key": "date", "label": "Date (MMDDYY)", "type": "date", "placeholder": "e.g. 032524",
                "default": "", "autofill": True
            }
        ]
    },
    "Legal": {
        "client_label": "Client / Matter Name",
        "summary": "Legal workflow with matter/case number, document type, description, and document date.",
        "default_filename_template": "{client}_{matter_number}_{document_type}_{description}_{date}",
        "fields": [
            {
                "key": "matter_number", "label": "Matter / Case #", "type": "text",
                "placeholder": "Matter or case number", "default": "", "autofill": True
            },
            {
                "key": "document_type", "label": "Document Type", "type": "text",
                "placeholder": "e.g. Notice, Letter, Filing", "default": "", "autofill": True,
                "title_case": True
            },
            {
                "key": "description", "label": "Description", "type": "text",
                "placeholder": "Description", "default": "", "autofill": True, "title_case": True,
                "tooltip": "Set a Legal-specific default Description and autofill behavior in Settings > Workspaces."
            },
            {
                "key": "date", "label": "Document Date (MMDDYY)", "type": "date",
                "placeholder": "e.g. 081926", "default": "", "autofill": True
            }
        ]
    }
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
    "suppressFutureDateWarning": False,
    "check_updates_on_startup": True,
    # Legacy Accounting keys are retained so existing settings migrate cleanly.
    "autofill_description": True,
    "default_description": "POA",
    "filename_template": "{client}_{revoked}_{agency_description}_{date}",
    "default_workspace": "Accounting",
    "workspace_settings": {
        "Accounting": {
            "default_description": "POA",
            "autofill_description": True,
            "filename_template": "{client}_{revoked}_{agency_description}_{date}"
        },
        "Legal": {
            "default_description": "",
            "autofill_description": True,
            "filename_template": "{client}_{matter_number}_{document_type}_{description}_{date}"
        }
    }
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
    elif type == "undo":
        full_message = f"{timestamp} [UNDO/REDO] {message}"

    debug_log.append(full_message)
    print(full_message)

    try:
        with open(DEBUG_FILE, "a", encoding="utf-8") as f:
            f.write(full_message + "\n")
    except Exception as e:
        print(f"Failed to write debug log: {e}")
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
                },
                "CTkProgressBar": {
                    "corner_radius": 10,
                    "border_width": 0,
                    "fg_color": "#f7d6e0",
                    "progress_color": "#ff69b4",
                    "border_color": "#ffb6c1"
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
        },
        "CTkProgressBar": {
            "corner_radius": 10,
            "border_width": 0,
            "fg_color": "#3a3a3a",
            "progress_color": "#ff69b4",
            "border_color": "#ff85c1"
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
    version_str = version_str.strip().lower()

    if version_str.startswith("v"):
        version_str = version_str[1:]

    parts = version_str.split(".")
    numbers = []

    for part in parts:
        number = ""

        for char in part:
            if char.isdigit():
                number += char
            else:
                break

        numbers.append(int(number) if number else 0)

    while len(numbers) < 3:
        numbers.append(0)

    return tuple(numbers)

class CTkUndoEntry(ctk.CTkEntry):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._undo_stack = []
        self._redo_stack = []
        self._last_value = self.get()
        self._typing_timer = None

        self.after(10, self._bind_events)

    def _bind_events(self):
        try:
            self._entry.bind("<Key>", self._on_keypress)
            self._entry.bind("<Control-z>", self._undo)
            self._entry.bind("<Control-y>", self._redo)
            debug("[UNDO] Smart undo/redo system initialized", "undo")
        except Exception as e:
            debug(f"[UNDO] Failed to bind events: {e}", "error")

    def _on_keypress(self, event=None):
        keys_to_commit_immediately = ["Return", "Tab", "space"]

        if event.keysym in keys_to_commit_immediately:
            self._commit_snapshot()
            return

        if self._typing_timer:
            self.after_cancel(self._typing_timer)

        # Wait 600ms before committing this snapshot
        self._typing_timer = self.after(600, self._commit_snapshot)

    def _commit_snapshot(self):
        current = self.get()
        if current != self._last_value:
            self._undo_stack.append(self._last_value)
            self._redo_stack.clear()
            debug(f"[UNDO] Committed snapshot: '{self._last_value}'", "undo")
            self._last_value = current

    def _undo(self, event=None):
        self._commit_snapshot()  # Commit any unsaved change before undoing
        if self._undo_stack:
            prev = self._undo_stack.pop()
            self._redo_stack.append(self.get())
            debug(f"[UNDO] Reverted to '{prev}' | redo stack = {self._redo_stack}", "undo")
            self._last_value = prev
            self._entry.delete(0, "end")
            self._entry.insert(0, prev)
        else:
            debug("[UNDO] Nothing to undo.", "undo")
        return "break"

    def _redo(self, event=None):
        if self._redo_stack:
            next_val = self._redo_stack.pop()
            self._undo_stack.append(self.get())
            debug(f"[REDO] Reapplied '{next_val}' | undo stack = {self._undo_stack}", "undo")
            self._last_value = next_val
            self._entry.delete(0, "end")
            self._entry.insert(0, next_val)
        else:
            debug("[REDO] Nothing to redo.", "undo")
        return "break"

CTkEntry = CTkUndoEntry

class PDFSplitterApp(TkinterDnD.Tk):
    # ─── INITIALIZATION ───
    def __init__(self):
        super().__init__()
        self.start_time = time.perf_counter()

        try:
            self.iconbitmap(str(APP_ICON))
        except Exception as e:
            debug(f"Could not load app icon: {e}", "warning")

        self.pdf_sessions = {}
        self.settings = {}

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
        self.tutorial_active = False
        self.tutorial_pending = False
        self.tutorial_cancelled_this_session = False
        self._bound_key_sequences = []
        self._key_capture_bind_id = None

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        with open(DEBUG_FILE, "w", encoding="utf-8") as f:
            f.write("")

        if not self.check_license():
            self.destroy()
            return

        self.load_version_info()

        self.load_settings()

        self.font_size = self.settings.get("font_size", 12)
        self.font_family = self.settings.get("font_family", "Segoe UI")

        self.show_fullscreen_loading_overlay()
        self.finish_initialization()
    def finish_initialization(self):
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

        self.notebook = ctk.CTkTabview(self)
        self.notebook.pack(fill="both", expand=True)
        self.after(100, self._apply_tab_font_size)

        self.splitter_tab = self.notebook.add("Split & Rename")
        self.quick_splitter_tab = self.notebook.add("Quick Split")
        self.settings_tab = self.notebook.add("Settings")
        self.log_tab = self.notebook.add("Logs")
        self.about_tab = self.notebook.add("About")
        self.keybinds_tab = self.notebook.add("Keybinds")
        self.help_tab = self.notebook.add("Help")

        self.build_splitter_tab()
        self.build_quick_split_tab(self.quick_splitter_tab)
        self.build_about_tab(self.about_tab)
        self.build_settings_tab()
        self.build_log_tab()
        self.build_keybinds_tab()
        self.build_help_tab(self.help_tab)

        self._apply_tab_font_size()
        self.apply_keybinds()

        self.after(200, self.check_export_folder_prompt)

        if self.settings.get("check_updates_on_startup", True):
            self.after(1500, self.check_for_updates)

        self.make_client_folder_var = tk.BooleanVar(value=True)

        if self.settings.get("auto_restore_session", True):
            self.restore_previous_session()
        self.start_auto_save_sessions()

        self.after(1000, self.hide_loading_overlay)
        elapsed = time.perf_counter() - self.start_time
        debug(f"Startup completed in {elapsed:.2f} seconds", "debug")
    def check_for_updates(self):

        try:

            with urllib.request.urlopen(
                    VERSION_URL,
                    timeout=10
            ) as response:

                data = json.loads(
                    response.read().decode("utf-8")
                )

            remote_version = str(
                data.get("version", "")
            )

            changelog = data.get(
                "changelog",
                {}
            )

            if (
                    remote_version
                    and
                    parse_version(remote_version)
                    >
                    parse_version(CURRENT_VERSION)
            ):

                debug(
                    f"Update available: "
                    f"{CURRENT_VERSION} -> {remote_version}",
                    "update"
                )

                notes_list = changelog.get(
                    remote_version,
                    ["No changelog available."]
                )

                formatted = "\n".join(
                    f"• {line}"
                    for line in notes_list
                )

                confirm = messagebox.askyesno(
                    "Update Available",

                    f"A new version of CleanCutPDF is available!\n\n"

                    f"Current version: {CURRENT_VERSION}\n"
                    f"Latest version: {remote_version}\n\n"

                    f"Changes:\n{formatted}\n\n"

                    "Would you like to update now?"
                )

                if confirm:

                    debug(
                        "User accepted update.",
                        "update"
                    )

                    self.launch_updater()


                else:

                    debug(
                        "User postponed update.",
                        "update"
                    )


            else:

                debug(
                    f"App up to date: {CURRENT_VERSION}",
                    "update"
                )


        except Exception as e:

            # Startup update checks should NOT interrupt
            # normal use of CleanCutPDF.

            debug(
                f"Automatic update check failed: {e}",
                "error"
            )
    def check_for_updates_manual(self):

        try:

            with urllib.request.urlopen(
                    VERSION_URL,
                    timeout=10
            ) as response:

                data = json.loads(
                    response.read().decode("utf-8")
                )

            remote_version = str(
                data.get("version", "")
            )

            changelog = data.get(
                "changelog",
                {}
            )

            if (
                    remote_version
                    and
                    parse_version(remote_version)
                    >
                    parse_version(CURRENT_VERSION)
            ):

                notes_list = changelog.get(
                    remote_version,
                    ["No changelog available."]
                )

                formatted = "\n".join(
                    f"• {line}"
                    for line in notes_list
                )

                confirm = messagebox.askyesno(
                    "Update Available",

                    f"A new version of CleanCutPDF is available!\n\n"

                    f"Current version: {CURRENT_VERSION}\n"
                    f"Latest version: {remote_version}\n\n"

                    f"Changes:\n{formatted}\n\n"

                    "Would you like to update now?"
                )

                if confirm:
                    self.launch_updater()


            else:

                messagebox.showinfo(
                    "No Updates Available",
                    f"CleanCutPDF {CURRENT_VERSION} is up to date."
                )

                debug(
                    f"Manual update check: "
                    f"{CURRENT_VERSION} is current.",
                    "update"
                )


        except Exception as e:

            messagebox.showerror(
                "Update Check Failed",
                f"Could not check for updates:\n\n{e}"
            )

            debug(
                f"Manual update check failed: {e}",
                "error"
            )
    def load_version_info(self):

        # The installed version ALWAYS comes
        # from the code itself.
        self.current_version = CURRENT_VERSION

        self.version_info = {}
        self.changelog = []

        try:

            with urllib.request.urlopen(
                    VERSION_URL,
                    timeout=10
            ) as response:

                data = json.loads(
                    response.read().decode("utf-8")
                )

            self.version_info = data

            changelog = data.get(
                "changelog",
                {}
            )

            self.changelog = changelog.get(
                CURRENT_VERSION,
                []
            )

            debug(
                f"Installed CleanCutPDF version: "
                f"{CURRENT_VERSION}",
                "debug"
            )


        except Exception as e:

            # About page can still work even if
            # GitHub is unavailable.

            self.current_version = CURRENT_VERSION

            self.changelog = []

            debug(
                f"Could not load remote version info: {e}",
                "error"
            )
    def launch_updater(self):

        try:

            # ─────────────────────────────────────
            # INSTALLED / COMPILED VERSION
            # ─────────────────────────────────────

            if getattr(sys, "frozen", False):

                app_path = Path(sys.executable)

                updater_path = (
                        app_path.parent
                        / "CleanCutPDFUpdater.exe"
                )

                if not updater_path.exists():
                    messagebox.showerror(
                        "Updater Missing",
                        "CleanCutPDFUpdater.exe could not be found."
                    )

                    debug(
                        f"Updater missing: {updater_path}",
                        "error"
                    )

                    return

                debug(
                    f"Launching updater: {updater_path}",
                    "update"
                )

                subprocess.Popen([
                    str(updater_path),

                    "--current-version",
                    CURRENT_VERSION,

                    "--app",
                    str(app_path),

                    "--pid",
                    str(os.getpid())
                ])

                # Close CleanCutPDF so updater can replace EXE.
                self.after(
                    300,
                    self.destroy
                )


            # ─────────────────────────────────────
            # PYCHARM / DEVELOPMENT VERSION
            # ─────────────────────────────────────

            else:

                updater_path = (
                        Path(__file__).parent
                        / "update.py"
                )

                if not updater_path.exists():
                    messagebox.showerror(
                        "Updater Missing",
                        "update.py could not be found."
                    )

                    debug(
                        f"Updater missing: {updater_path}",
                        "error"
                    )

                    return

                debug(
                    f"Launching development updater: {updater_path}",
                    "update"
                )

                subprocess.Popen([
                    sys.executable,
                    str(updater_path),

                    "--current-version",
                    CURRENT_VERSION
                ])

                # IMPORTANT:
                # Don't close the main app when testing
                # from PyCharm
        except Exception as error:

            debug(
                f"Failed to launch updater: {error}",
                "error"
            )

            messagebox.showerror(
                "Updater Error",
                f"Could not launch the CleanCutPDF updater.\n\n{error}"
            )
    # ─── Loading UI ───
    def show_loading_overlay(self, message="Loading..."):
        debug("Starting loading overlay...", "debug")
        if hasattr(self, "loading_overlay") and self.loading_overlay and self.loading_overlay.winfo_exists():
            return

        # ─── Theme-Aware Colors ───
        theme = ctk.ThemeManager.theme

        bg_color = theme["CTk"]["fg_color"]
        if isinstance(bg_color, list):
            bg_color = bg_color[0] if ctk.get_appearance_mode() == "Light" else bg_color[1]

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
        debug("Stopping loading overlay...", "debug")
        if hasattr(self, 'loading_overlay') and self.loading_overlay.winfo_exists():
            self.loading_overlay.destroy()
    def _show_brief_loading_overlay(self):
        self.show_loading_overlay()
        self.after(400, self.hide_loading_overlay)
    def show_fullscreen_loading_overlay(self):
        debug("Creating fullscreen loading overlay...", "debug")

        if hasattr(self, "loading_overlay") and self.loading_overlay and self.loading_overlay.winfo_exists():
            self.loading_overlay.destroy()

        self.loading_overlay = tk.Toplevel(self)
        self.loading_overlay.overrideredirect(True)
        self.loading_overlay.attributes("-topmost", True)
        self.loading_overlay.grab_set()

        self.update_idletasks()

        width = self.winfo_width()
        height = self.winfo_height()

        x = self.winfo_rootx()
        y = self.winfo_rooty()

        self.loading_overlay.geometry(
            f"{width}x{height}+{x}+{y}"
        )

        theme = ctk.ThemeManager.theme
        mode = ctk.get_appearance_mode()

        bg_color = theme.get("CTk", {}).get("fg_color", "#1e1e1e")
        if isinstance(bg_color, list):
            bg_color = bg_color[0] if mode == "Light" else bg_color[1]

        active_color = theme.get("CTkButton", {}).get("fg_color", "#ff69b4")
        if isinstance(active_color, list):
            active_color = active_color[0] if mode == "Light" else active_color[1]

        inactive_color = theme.get("CTkLabel", {}).get("text_color_disabled", "#aaaaaa")
        if isinstance(inactive_color, list):
            inactive_color = inactive_color[0] if mode == "Light" else inactive_color[1]

        self.loading_overlay.configure(bg=bg_color)
        text_color = "black" if mode == "Light" else "white"

        center_frame = tk.Frame(self.loading_overlay, bg=bg_color)
        center_frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            center_frame,
            text="Loading...",
            fg=text_color,
            bg=bg_color,
            font=(self.font_family, self.font_size + 2, "bold")
        ).pack(pady=(0, 8))

        canvas_width = 96
        canvas_height = 24
        canvas = tk.Canvas(
            center_frame,
            bg=bg_color,
            highlightthickness=0,
            width=canvas_width,
            height=canvas_height
        )
        canvas.pack()

        diameter = 12
        gap = 18
        total_width = diameter * 3 + gap * 2
        start_x = (canvas_width - total_width) / 2
        y0 = (canvas_height - diameter) / 2

        dots = []
        for i in range(3):
            x0 = start_x + i * (diameter + gap)
            dots.append(canvas.create_oval(
                x0, y0, x0 + diameter, y0 + diameter,
                fill=inactive_color, outline=""
            ))

        def animate(index=0):
            try:
                if not self.loading_overlay.winfo_exists():
                    return
                for i, dot in enumerate(dots):
                    canvas.itemconfig(dot, fill=active_color if i == index else inactive_color)
                self.loading_overlay.after(200, animate, (index + 1) % len(dots))
            except tk.TclError:
                return

        animate()
        debug("Fullscreen loading overlay centered", "debug")

    # ─── Settings ───
    def load_settings(self):
        # Deep-copy because workspace_settings contains nested dictionaries.
        self.settings = copy.deepcopy(DEFAULT_SETTINGS)
        user_settings = {}
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                user_settings = json.load(f)

            if not isinstance(user_settings, dict):
                raise ValueError("Invalid settings format")

            # Merge ordinary top-level settings first.
            for key, value in user_settings.items():
                if key != "workspace_settings":
                    self.settings[key] = value

            # Merge each workspace independently so new workspace keys can be added safely.
            saved_workspace_settings = user_settings.get("workspace_settings", {})
            if isinstance(saved_workspace_settings, dict):
                for workspace_name in WORKSPACES:
                    saved = saved_workspace_settings.get(workspace_name, {})
                    if isinstance(saved, dict):
                        self.settings["workspace_settings"][workspace_name].update(saved)

            # Migrate the pre-workspace Accounting settings into the Accounting profile.
            # Only do this when the old settings file has no workspace_settings object yet.
            if "workspace_settings" not in user_settings:
                accounting = self.settings["workspace_settings"]["Accounting"]
                accounting["default_description"] = user_settings.get("default_description", "POA")
                accounting["autofill_description"] = user_settings.get("autofill_description", True)
                accounting["filename_template"] = user_settings.get(
                    "filename_template",
                    WORKSPACES["Accounting"]["default_filename_template"]
                )

        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            debug("Creating fresh settings.json with default values", "error")

        if self.settings.get("default_workspace") not in WORKSPACES:
            self.settings["default_workspace"] = "Accounting"

        # Keep old Accounting keys synchronized for backward compatibility.
        accounting = self.settings["workspace_settings"]["Accounting"]
        self.settings["default_description"] = accounting.get("default_description", "POA")
        self.settings["autofill_description"] = accounting.get("autofill_description", True)
        self.settings["filename_template"] = accounting.get(
            "filename_template",
            WORKSPACES["Accounting"]["default_filename_template"]
        )

        self.save_settings()

        try:
            with open(KEYBINDS_FILE, "r", encoding="utf-8") as f:
                file_keybinds = json.load(f)
                if not isinstance(file_keybinds, dict):
                    raise ValueError("Keybinds file must be a dictionary")
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            debug("Generating default keybinds", "error")
            file_keybinds = {}

        self.keybindings = {**DEFAULT_KEYBINDS, **file_keybinds}

        if self.keybindings != file_keybinds:
            with open(KEYBINDS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.keybindings, f, indent=2)
    def save_settings(self):
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(self.settings, f, indent=2)
    def save_sessions(self):
        data = []
        for name, session in self.pdf_sessions.items():
            self.capture_workspace_data(session)

            # Preserve an Accounting-shaped `parts` list for backward compatibility
            # with older session files while storing the full workspace-aware data too.
            legacy_parts = copy.deepcopy(
                session.get("workspace_data", {}).get("Accounting", [])
            )

            data.append({
                "file_path": str(session["path"]),
                "client_name": session["client_name_var"].get(),
                "workspace": session.get("workspace", "Accounting"),
                "workspace_data": copy.deepcopy(session.get("workspace_data", {})),
                "parts": legacy_parts
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
                legacy_parts = item.get("parts", [])
                workspace = item.get("workspace", "Accounting")
                if workspace not in WORKSPACES:
                    workspace = "Accounting"

                workspace_data = item.get("workspace_data", {})
                if not isinstance(workspace_data, dict):
                    workspace_data = {}

                # Old session files had only `parts`; treat those as Accounting data.
                if not workspace_data and legacy_parts:
                    workspace_data = {"Accounting": copy.deepcopy(legacy_parts)}

                if not path or not Path(path).exists():
                    continue

                pdf_name = Path(path).stem
                if pdf_name in self.pdf_sessions:
                    continue

                reader = PdfReader(path)
                current_rows = workspace_data.get(workspace, [])
                range_source = current_rows or legacy_parts
                ranges = (
                    [p["range"] for p in range_source if "range" in p]
                    if range_source
                    else self.detect_split_ranges_from_reader(reader)
                )

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
                    "workspace": workspace,
                    "workspace_data": copy.deepcopy(workspace_data),
                    "last_exported_files": [],
                    "widgets_to_scale": []
                }
                self.pdf_sessions[pdf_name] = session
                self.render_splitter_tab(tab, session)

        except Exception as e:
            messagebox.showwarning("Session Restore Failed", str(e))
            debug(f"Session restore error: {e}", "error")
    def check_future_date(self, raw_date, callback_on_confirm):
        try:
            today = datetime.date.today()
            normalized = self.format_date(raw_date)
            entered_date = datetime.datetime.strptime(normalized, "%m-%d-%Y").date()
        except Exception:
            debug(f"Invalid date format: {raw_date}", "debug")
            return  # skip if invalid

        if entered_date <= today:
            return

        if self.settings.get("suppressFutureDateWarning", False):
            return

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
                if hasattr(self, "future_date_popup_var"):
                    self.future_date_popup_var.set(False)
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
        bubble_color, border_color = self.get_log_bubble_colors()

        wrapper = ctk.CTkFrame(tab)
        wrapper.pack(fill="both", expand=True, padx=20, pady=20)

        bubble = ctk.CTkFrame(wrapper, fg_color=bubble_color, border_color=border_color, border_width=3, corner_radius=10)
        bubble.pack(padx=40, pady=30, fill="both", expand=True)

        ctk.CTkLabel(
            bubble,
            text="⚡ Quick Split Mode",
            font=(self.font_family, self.font_size + 4, "bold"),
            text_color="#AA0055"
        ).pack(pady=(20, 5))

        ctk.CTkLabel(
            bubble,
            text="Perfect for batch-scanning single documents for multiple clients.",
            font=(self.font_family, self.font_size - 1),
            text_color="#888888"
        ).pack(pady=(0, 10))

        usage_points = [
            "• Use when each client has only one document",
            "• Place SPLIT HERE sheets between each client’s file",
            "• Scan everything in one pass",
            "• Files will be auto-split and named 'Part 01', 'Part 02', etc.",
            "• Saved to: Quick Split Files/YYYY-MM-DD"
        ]

        for point in usage_points:
            ctk.CTkLabel(
                bubble,
                text=point,
                font=(self.font_family, self.font_size),
                anchor="w",
                justify="left",
                wraplength=700
            ).pack(anchor="center", padx=40, pady=2)

        ctk.CTkButton(
            bubble,
            text="➕ Open PDF",
            font=(self.font_family, self.font_size),
            command=self.load_quick_split_pdf,
            width=160
        ).pack(pady=20)

        ctk.CTkLabel(
            bubble,
            text="You can also drag and drop one or multiple PDFs into this area.",
            font=(self.font_family, self.font_size - 1),
            text_color="#888888"
        ).pack(pady=(0, 20))

        # Enable drag-and-drop
        wrapper.drop_target_register(DND_FILES)
        wrapper.dnd_bind('<<Drop>>', self.handle_quick_drop)
    def build_quick_split_tab2(self, tab):
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
            "saved into the folder called \"Quick Split Files\""
        )
        ctk.CTkLabel(wrapper, text=desc, font=(self.font_family, self.font_size), wraplength=600, justify="center").pack(pady=10)

        open_button = ctk.CTkButton(wrapper, text="➕ Open PDF", command=self.load_quick_split_pdf, font=(self.font_family, self.font_size))
        open_button.pack(pady=10)

        drag_and_drop_label = "You can drag and drop one or multiple files here"
        ctk.CTkLabel(wrapper, text=drag_and_drop_label, font=(self.font_family, self.font_size), wraplength=600, justify="center").pack(pady=10)
    def build_settings_tab(self):
        self.settings_sidebar_buttons = {}
        self.settings_sections = {}

        container = ctk.CTkFrame(self.settings_tab)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # Left: Vertical menu
        menu = ctk.CTkFrame(container, width=150)
        menu.pack(side="left", fill="y", padx=(0, 10))

        # Right: Content area
        self.settings_stack = ctk.CTkFrame(container)
        self.settings_stack.pack(side="left", fill="both", expand=True)

        for section in ["Appearance", "Export", "Behavior", "Workspaces", "License"]:
            frame = ctk.CTkFrame(self.settings_stack)
            frame.pack(fill="both", expand=True)
            frame.pack_forget()  # Hide initially
            self.settings_sections[section] = frame

        # Populate each section
        self._build_appearance_section(self.settings_sections["Appearance"])
        self._build_export_section(self.settings_sections["Export"])
        self._build_behavior_section(self.settings_sections["Behavior"])
        self._build_workspaces_section(self.settings_sections["Workspaces"])
        self._build_license_section(self.settings_sections["License"])

        # Sidebar buttons
        for section in self.settings_sections:
            btn = ctk.CTkButton(
                menu,
                text=section,
                corner_radius=8,
                fg_color="transparent",  # default color
                text_color=("black", "white"),
                hover_color="#cccccc",
                command=lambda s=section: self._show_settings_section(s)
            )
            btn.pack(fill="x", pady=5)
            self.settings_sidebar_buttons[section] = btn


        self._show_settings_section("Appearance")
    def build_about_tab(self, tab):
        scroll = ctk.CTkScrollableFrame(tab)
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        title = ctk.CTkLabel(scroll, text="CleanCutPDF", font=(self.font_family, self.font_size + 6, "bold"))
        title.pack(pady=(10, 4))

        version_label = ctk.CTkLabel(scroll, text=f"Version {self.current_version}", font=(self.font_family, self.font_size + 1))
        version_label.pack()

        ctk.CTkLabel(scroll, text=f"Licensed to: {self.licensed_company}", font=(self.font_family, self.font_size - 1)).pack(pady=(2, 20))

        if self.changelog:
            ctk.CTkLabel(scroll, text="What's New:", font=(self.font_family, self.font_size + 6, "bold")).pack(anchor="center", padx=10)
            for line in self.changelog:
                ctk.CTkLabel(scroll, text="• " + line, font=(self.font_family, self.font_size), wraplength=880, anchor="center", justify="left").pack(anchor="center", padx=20, pady=2)
    def build_log_tab(self):
        search_frame = ctk.CTkFrame(self.log_tab)
        search_frame.pack(fill="x", padx=10, pady=10)

        self.search_var = ctk.StringVar()
        self.sort_mode_var = ctk.StringVar(value="Date ↓")

        ctk.CTkLabel(search_frame, text="Search:").pack(side="left", padx=(0, 5))
        self.search_entry = CTkEntry(search_frame, textvariable=self.search_var)
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
        self.keybind_vars = {}

        bubble_color, border_color = self.get_log_bubble_colors()

        wrapper = ctk.CTkFrame(
            self.keybinds_tab,
            fg_color=bubble_color,
            border_color=border_color,
            border_width=3,
            corner_radius=10
        )
        wrapper.pack(fill="both", expand=True, padx=20, pady=20)

        title = ctk.CTkLabel(wrapper, text="🎯 Keyboard Shortcuts", font=(self.font_family, self.font_size + 4, "bold"))
        title.pack(pady=(10, 4))

        desc = ctk.CTkLabel(wrapper, text="Click a shortcut to change it. Press your new combo and it will be saved.",
                            font=(self.font_family, self.font_size - 1),
                            text_color="#888888")
        desc.pack(pady=(0, 10))

        scroll_frame = ctk.CTkScrollableFrame(wrapper, width=800, height=400)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        for idx, (action, combo) in enumerate(self.keybindings.items()):
            row = ctk.CTkFrame(scroll_frame, fg_color=bubble_color, corner_radius=6)
            row.pack(fill="x", padx=10, pady=4)

            label = ctk.CTkLabel(row, text=action, anchor="w", font=(self.font_family, self.font_size))
            label.pack(side="left", padx=10, pady=6, fill="x", expand=True)

            var = ctk.StringVar(value=combo)
            shortcut_box = ctk.CTkLabel(
                row,
                textvariable=var,
                font=(self.font_family, self.font_size),
                fg_color="#eeeeee",
                text_color="black",
                corner_radius=6,
                width=100,
                anchor="center",
                cursor="hand2"
            )
            shortcut_box.pack(side="right", padx=10, pady=6)

            # Bind click
            self.add_tooltip(shortcut_box, "Click to change keybind")
            shortcut_box.bind("<Button-1>", lambda e, a=action, lbl=shortcut_box: self.start_keybind_input(a, lbl))

            self.keybind_vars[action] = var

        # Save Button
        theme = ctk.ThemeManager.theme
        btn_color = theme.get("CTkButton", {}).get("fg_color", "#3B8ED0")

        if isinstance(btn_color, list):
            btn_color = btn_color[0] if ctk.get_appearance_mode() == "Light" else btn_color[1]

        ctk.CTkButton(wrapper, text="💾 Save Keybinds", command=self.save_keybinds, fg_color=btn_color).pack(pady=15)
    def build_help_tab(self, tab):
        scrollable = ctk.CTkScrollableFrame(tab, width=880)
        scrollable.pack(fill="both", expand=True, padx=20, pady=20)

        bubble_color, border_color = self.get_log_bubble_colors()

        font_title = (self.font_family, self.font_size + 3, "bold")
        font_section = (self.font_family, self.font_size + 1, "bold")
        font_body = (self.font_family, self.font_size)
        font_code = (self.font_family, self.font_size - 1, "italic")

        wrap_factor = 800
        label_padx = 15

        # ─── Bubble 1: Split & Rename ───
        bubble1 = ctk.CTkFrame(scrollable, fg_color=bubble_color, border_color=border_color, border_width=3, corner_radius=10)
        bubble1.pack(fill="x", pady=10, padx=10)

        ctk.CTkLabel(bubble1, text="🧩 Using Split & Rename", font=font_title, text_color="#3B8ED0").pack(anchor="w", padx=label_padx, pady=(10, 4))
        ctk.CTkLabel(bubble1, text="Best for: Organizing multiple documents per client", font=font_section).pack(anchor="w", padx=label_padx)
        ctk.CTkLabel(bubble1, text="Example: Scanning large sets of old legal files", font=font_body).pack(anchor="w", padx=label_padx, pady=(0, 5))

        for tip in [
            "• Use when a client has more than one document that needs to be saved separately",
            "• Group by client: Stack each client’s documents together",
            "• Place SPLIT HERE sheets between each document in the client’s stack",
            "• Scan the entire client stack in one go"
        ]:
            ctk.CTkLabel(bubble1, text=tip, font=font_body, anchor="w", wraplength=wrap_factor, justify="left").pack(anchor="w", padx=label_padx, pady=2)

        ctk.CTkLabel(bubble1, text="In the app, use Split & Rename to:", font=font_body).pack(anchor="w", padx=label_padx, pady=(8, 2))
        for action in [
            "○ Automatically detect splits",
            "○ Enter the client’s name once",
            "○ Fill in info like agency, description, and date for each file",
            "○ Save each document with custom names"
        ]:
            ctk.CTkLabel(bubble1, text=action, font=font_body, anchor="w", wraplength=wrap_factor, justify="left", padx=20).pack(anchor="w", padx=label_padx)

        ctk.CTkLabel(bubble1, text="📝 Why it’s helpful:", font=font_section).pack(anchor="w", padx=label_padx, pady=(10, 2))
        ctk.CTkLabel(bubble1, text=(
            "This saves time compared to manually separating, reorienting, and renaming each file individually. "
            "Ideal when scanning lots of documents for multiple clients where each client has several items."
        ), font=font_body, wraplength=wrap_factor, justify="left").pack(anchor="w", padx=label_padx, pady=(0, 10))

        # ─── Bubble 2: Quick Split ───
        bubble2 = ctk.CTkFrame(scrollable, fg_color=bubble_color, border_color=border_color, border_width=3, corner_radius=10)
        bubble2.pack(fill="x", pady=10, padx=10)

        ctk.CTkLabel(bubble2, text="⚡ Using Quick Split", font=font_title, text_color="#AA0055").pack(anchor="w", padx=label_padx, pady=(10, 4))
        ctk.CTkLabel(bubble2, text="Best for: Scanning one document per client", font=font_section).pack(anchor="w", padx=label_padx)
        ctk.CTkLabel(bubble2, text="Example: Uploading 50+ single POA revocations to the IRS", font=font_body).pack(anchor="w", padx=label_padx, pady=(0, 5))

        for tip in [
            "• Place SPLIT HERE sheets between each client’s document",
            "• Scan all client documents in one batch"
        ]:
            ctk.CTkLabel(bubble2, text=tip, font=font_body, anchor="w", wraplength=wrap_factor, justify="left").pack(anchor="w", padx=label_padx, pady=2)

        ctk.CTkLabel(bubble2, text="Use Quick Split to:", font=font_body).pack(anchor="w", padx=label_padx, pady=(8, 2))
        for action in [
            "○ Instantly split the file at each marker",
            "○ Auto-name each part:"
        ]:
            ctk.CTkLabel(bubble2, text=action, font=font_body, anchor="w", wraplength=wrap_factor, justify="left", padx=20).pack(anchor="w", padx=label_padx)

        ctk.CTkLabel(bubble2, text="[Original Filename] – Part 01, Part 02, etc.", font=font_code).pack(anchor="w", padx=label_padx + 25)
        ctk.CTkLabel(bubble2, text="○ Save them to a designated folder", font=font_body).pack(anchor="w", padx=label_padx + 20, pady=(0, 8))

        ctk.CTkLabel(bubble2, text="📥 Optional:", font=font_section).pack(anchor="w", padx=label_padx)
        ctk.CTkLabel(bubble2, text="Drag into the Split & Rename afterward if custom file names are needed",
                     font=font_body, wraplength=wrap_factor, justify="left").pack(anchor="w", padx=label_padx, pady=2)

        ctk.CTkLabel(bubble2, text="📝 Why it’s helpful:", font=font_section).pack(anchor="w", padx=label_padx, pady=(10, 2))
        ctk.CTkLabel(bubble2, text=(
            "Saves time by avoiding repetitive scan/load/unload cycles. "
            "Great when each client only has one file and you want to keep things moving quickly."
        ), font=font_body, wraplength=wrap_factor, justify="left").pack(anchor="w", padx=label_padx, pady=(0, 10))

        # ─── Bubble 3: Printing Tips ───
        bubble3 = ctk.CTkFrame(scrollable, fg_color=bubble_color, border_color=border_color, border_width=3, corner_radius=10)
        bubble3.pack(fill="x", pady=10, padx=10)

        ctk.CTkLabel(bubble3, text="🖨️ Printing SPLIT HERE Sheets", font=font_title, text_color="#228B22").pack(anchor="w", padx=label_padx, pady=(10, 4))

        tips = [
            "• Use brightly colored paper to make SPLIT HERE sheets stand out",
            "• Clearly print 'SPLIT HERE' in large, bold text (use the template below if needed)",
            "• Select 'Multiple Sized Originals' when scanning",
            "• Insert SPLIT HERE sheets between documents — not between clients",
            "• Sort files into double- and single-sided batches before scanning",
            "• Use tabs or sticky notes to make sheets easier to spot",
            "• Check that SPLIT HERE text is legible before printing",
            "• Place pages in order during scanning to avoid mistakes"
        ]
        for line in tips:
            ctk.CTkLabel(bubble3, text=line, font=font_body, anchor="w", wraplength=wrap_factor, justify="left").pack(anchor="w", padx=label_padx, pady=2)

        # Download button
        ctk.CTkButton(
            bubble3,
            text="📥 Download SPLIT HERE Template",
            font=(self.font_family, self.font_size),
            command=self.download_split_here_sheet
        ).pack(pady=(15, 10), padx=label_padx, anchor="w")
    def rebuild_ui(self):
            debug("Rebuilding UI", "debug")
            current_tab = self.notebook.get()

            for session in self.pdf_sessions.values():
                self.capture_workspace_data(session)

            self.notebook.destroy()
            self.notebook = ctk.CTkTabview(self)
            self.notebook.pack(fill="both", expand=True)

            self.splitter_tab = self.notebook.add("Split & Rename")
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
            self.build_about_tab(self.about_tab)
            self.build_keybinds_tab()
            self.build_help_tab(self.help_tab)

            self._apply_font_size()

            try:
                self.notebook.set(current_tab)
            except:
                pass

            if hasattr(self, "canvas"):
                self._check_scrollbar_visibility()

            for pdf_name, session in self.pdf_sessions.items():
                tab_label = session["tab_label"]
                tab = self.pdf_tabview.add(tab_label)
                session["tab"] = tab
                self.render_splitter_tab(tab, session)

            self._apply_font_size()
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

        theme = ctk.ThemeManager.theme
        fg_color = theme.get("CTkButton", {}).get("fg_color", "#3B8ED0")

        if isinstance(fg_color, list):
            fg_color = fg_color[0] if ctk.get_appearance_mode() == "Light" else fg_color[1]

        for section, button in self.settings_sidebar_buttons.items():
            if section == name:
                button.configure(fg_color=fg_color, text_color="white")
            else:
                button.configure(fg_color="transparent", text_color=("black", "white"))
    def _build_appearance_section(self, parent):

        bubble_color, border_color = self.get_log_bubble_colors()

        # ─── Theme Settings ───
        theme_bubble = ctk.CTkFrame(parent, fg_color=bubble_color, border_color=border_color, border_width=2, corner_radius=10)
        theme_bubble.pack(padx=10, pady=(15, 10), fill="x")

        ctk.CTkLabel(theme_bubble, text="🎨 Theme Settings", font=(self.font_family, self.font_size + 2, "bold")).pack(anchor="center", padx=15, pady=(10, 5))

        self.theme_var = ctk.StringVar(value=self.theme)
        theme_menu = ctk.CTkOptionMenu(theme_bubble, values=list(THEMES.keys()), variable=self.theme_var, command=self.change_theme)
        theme_menu.pack(padx=15, pady=(0, 10))
        self.settings_widgets_to_scale.append(theme_menu)

        # ─── Font Settings ───
        font_bubble = ctk.CTkFrame(parent, fg_color=bubble_color, border_color=border_color, border_width=2, corner_radius=10)
        font_bubble.pack(padx=10, pady=(0, 20), fill="x")

        ctk.CTkLabel(font_bubble, text="🔠 Font Settings", font=(self.font_family, self.font_size + 2, "bold")).pack(anchor="center", padx=15, pady=(10, 5))

        self.font_size_var = ctk.IntVar(value=self.font_size)
        font_slider = ctk.CTkSlider(font_bubble, from_=12, to=32, number_of_steps=10, variable=self.font_size_var, command=self.update_font_size)
        font_slider.pack(padx=15, pady=5)
        self.settings_widgets_to_scale.append(font_slider)

        self.font_family_var = ctk.StringVar(value=self.font_family)
        font_menu = ctk.CTkOptionMenu(font_bubble, values=FONTS, variable=self.font_family_var, command=self.update_font_family)
        font_menu.pack(padx=15, pady=(0, 10))
        self.settings_widgets_to_scale.append(font_menu)
    def _build_export_section(self, parent):
        bubble_color, border_color = self.get_log_bubble_colors()

        folder_bubble = ctk.CTkFrame(parent, fg_color=bubble_color, border_color=border_color, border_width=2, corner_radius=10)
        folder_bubble.pack(padx=10, pady=(15, 10), fill="x")

        ctk.CTkLabel(
            folder_bubble,
            text="📁 Default Export Folder",
            font=(self.font_family, self.font_size + 2, "bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))

        self.export_folder_var = ctk.StringVar(value=self.settings.get("export_folder", "Not Set"))
        export_row = ctk.CTkFrame(folder_bubble, fg_color="transparent")
        export_row.pack(padx=15, pady=(0, 10), fill="x")

        self.export_display = CTkEntry(export_row, textvariable=self.export_folder_var, state="disabled")
        self.export_display.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.settings_widgets_to_scale.append(self.export_display)

        browse_button = ctk.CTkButton(export_row, text="Browse...", command=self.set_export_folder)
        browse_button.pack(side="left")
        self.settings_widgets_to_scale.append(browse_button)

        options_bubble = ctk.CTkFrame(parent, fg_color=bubble_color, border_color=border_color, border_width=2, corner_radius=10)
        options_bubble.pack(padx=10, pady=(0, 20), fill="x")

        ctk.CTkLabel(
            options_bubble,
            text="⚙ Export Options",
            font=(self.font_family, self.font_size + 2, "bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))

        self.export_log_var = ctk.BooleanVar(value=self.settings.get("export_log_enabled", True))
        log_checkbox = ctk.CTkCheckBox(
            options_bubble,
            text="Generate Export Log",
            variable=self.export_log_var,
            command=self.update_export_log_setting
        )
        log_checkbox.pack(anchor="w", padx=20, pady=5)
        self.settings_widgets_to_scale.append(log_checkbox)

        ctk.CTkLabel(
            options_bubble,
            text="Workspace-specific filename formats are configured in Settings > Workspaces.",
            font=(self.font_family, max(10, self.font_size - 1)),
            text_color="#888888",
            wraplength=720,
            justify="left"
        ).pack(anchor="w", padx=20, pady=(8, 12))
    def _build_behavior_section(self, parent):
        font = (self.font_family, self.font_size)
        bubble_color, border_color = self.get_log_bubble_colors()

        # ─── File Processing ───
        file_bubble = ctk.CTkFrame(parent, fg_color=bubble_color, border_color=border_color, border_width=2, corner_radius=10)
        file_bubble.pack(padx=10, pady=(15, 10), fill="x")

        ctk.CTkLabel(file_bubble, text="🗂 File Processing", font=(self.font_family, self.font_size + 2, "bold")).pack(anchor="w", padx=15, pady=(10, 5))

        self.remove_blank_var = ctk.BooleanVar(value=self.settings.get("remove_blank_pages", True))
        blank_checkbox = ctk.CTkCheckBox(file_bubble, text="Remove Blank Pages Automatically", variable=self.remove_blank_var, command=self.update_remove_blank_setting)
        blank_checkbox.pack(anchor="w", padx=20, pady=5)
        self.settings_widgets_to_scale.append(blank_checkbox)

        ctk.CTkLabel(
            file_bubble,
            text="Description defaults and autofill are configured separately for each workspace in Settings > Workspaces.",
            font=(self.font_family, max(10, self.font_size - 1)),
            text_color="#888888",
            wraplength=700,
            justify="left"
        ).pack(anchor="w", padx=20, pady=(6, 10))

        # ─── Startup Behavior ───
        startup_bubble = ctk.CTkFrame(parent, fg_color=bubble_color, border_color=border_color, border_width=2, corner_radius=10)
        startup_bubble.pack(padx=10, pady=(0, 10), fill="x")

        ctk.CTkLabel(startup_bubble, text="🚀 Startup Behavior", font=(self.font_family, self.font_size + 2, "bold")).pack(anchor="w", padx=15, pady=(10, 5))

        self.auto_restore_var = ctk.BooleanVar(value=self.settings.get("auto_restore_session", True))
        restore_checkbox = ctk.CTkCheckBox(startup_bubble, text="Auto-Restore Previous Session", variable=self.auto_restore_var, command=self.update_auto_restore_setting)
        restore_checkbox.pack(anchor="w", padx=20, pady=5)
        self.settings_widgets_to_scale.append(restore_checkbox)

        self.check_updates_var = ctk.BooleanVar(value=self.settings.get("check_updates_on_startup", True))
        updates_checkbox = ctk.CTkCheckBox(startup_bubble, text="Check for Updates on Startup", variable=self.check_updates_var, command=lambda: self.save_setting("check_updates_on_startup", self.check_updates_var.get()))
        updates_checkbox.pack(anchor="w", padx=20, pady=(0, 10))
        self.settings_widgets_to_scale.append(updates_checkbox)

        # ─── Date Warning ───
        date_bubble = ctk.CTkFrame(parent, fg_color=bubble_color, border_color=border_color, border_width=2, corner_radius=10)
        date_bubble.pack(padx=10, pady=(0, 10), fill="x")

        ctk.CTkLabel(date_bubble, text="📅 Date Warnings", font=(self.font_family, self.font_size + 2, "bold")).pack(anchor="w", padx=15, pady=(10, 5))

        self.future_date_popup_var = ctk.BooleanVar(value=not self.settings.get("suppressFutureDateWarning", False))
        future_checkbox = ctk.CTkCheckBox(date_bubble, text="Warn me when I enter a future date", variable=self.future_date_popup_var, command=self.update_future_date_setting)
        future_checkbox.pack(anchor="w", padx=20, pady=(0, 10))
        self.settings_widgets_to_scale.append(future_checkbox)

        # ─── Tools ───
        tools_bubble = ctk.CTkFrame(parent, fg_color=bubble_color, border_color=border_color, border_width=2, corner_radius=10)
        tools_bubble.pack(padx=10, pady=(0, 20), fill="x")

        ctk.CTkLabel(tools_bubble, text="🛠 Tools", font=(self.font_family, self.font_size + 2, "bold")).pack(anchor="w", padx=15, pady=(10, 5))

        tutorial_btn = ctk.CTkButton(
            tools_bubble,
            text="📘 Run Tutorial Again",
            command=lambda: self.start_tutorial(manual=True)
        )
        tutorial_btn.pack(anchor="w", padx=15, pady=(0, 10))
        self.settings_widgets_to_scale.append(tutorial_btn)

        update_btn = ctk.CTkButton(tools_bubble, text="📘 Check for Updates", command=self.check_for_updates_manual)
        update_btn.pack(anchor="w", padx=15, pady=(0, 10))
        self.settings_widgets_to_scale.append(update_btn)
    def _build_workspaces_section(self, parent):
        bubble_color, border_color = self.get_log_bubble_colors()

        selector_bubble = ctk.CTkFrame(
            parent,
            fg_color=bubble_color,
            border_color=border_color,
            border_width=2,
            corner_radius=10
        )
        selector_bubble.pack(padx=10, pady=(15, 10), fill="x")

        ctk.CTkLabel(
            selector_bubble,
            text="🗂 Workspace Profiles",
            font=(self.font_family, self.font_size + 2, "bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))

        ctk.CTkLabel(
            selector_bubble,
            text="Each workspace can use different fields, Description defaults, autofill behavior, and filename rules.",
            font=(self.font_family, max(10, self.font_size - 1)),
            text_color="#888888",
            wraplength=720,
            justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 8))

        self.workspace_settings_selector_var = ctk.StringVar(
            value=self.settings.get("default_workspace", "Accounting")
        )
        selector = ctk.CTkOptionMenu(
            selector_bubble,
            values=list(WORKSPACES.keys()),
            variable=self.workspace_settings_selector_var,
            command=self.refresh_workspace_settings_editor
        )
        selector.pack(anchor="w", padx=15, pady=(0, 12))
        self.settings_widgets_to_scale.append(selector)

        self.workspace_settings_editor = ctk.CTkFrame(parent, fg_color="transparent")
        self.workspace_settings_editor.pack(fill="both", expand=True, padx=10, pady=(0, 20))
        self.refresh_workspace_settings_editor(self.workspace_settings_selector_var.get())

    def refresh_workspace_settings_editor(self, workspace_name):
        if workspace_name not in WORKSPACES:
            workspace_name = "Accounting"

        self.workspace_settings_selector_var.set(workspace_name)
        for child in self.workspace_settings_editor.winfo_children():
            child.destroy()

        bubble_color, border_color = self.get_log_bubble_colors()
        profile = WORKSPACES[workspace_name]
        settings = self.get_workspace_settings(workspace_name)

        profile_bubble = ctk.CTkFrame(
            self.workspace_settings_editor,
            fg_color=bubble_color,
            border_color=border_color,
            border_width=2,
            corner_radius=10
        )
        profile_bubble.pack(fill="x")

        ctk.CTkLabel(
            profile_bubble,
            text=f"{workspace_name} Workspace",
            font=(self.font_family, self.font_size + 2, "bold")
        ).pack(anchor="w", padx=15, pady=(12, 3))

        ctk.CTkLabel(
            profile_bubble,
            text=profile.get("summary", ""),
            font=(self.font_family, max(10, self.font_size - 1)),
            text_color="#888888",
            wraplength=700,
            justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 10))

        ctk.CTkLabel(profile_bubble, text="Default Description").pack(anchor="w", padx=15, pady=(3, 2))
        default_var = ctk.StringVar(value=settings.get("default_description", ""))
        default_entry = CTkEntry(profile_bubble, textvariable=default_var, placeholder_text="Leave blank for no default")
        default_entry.pack(fill="x", padx=15, pady=(0, 6))
        default_entry.bind(
            "<FocusOut>",
            lambda _e, w=workspace_name, v=default_var: self.save_workspace_setting(w, "default_description", v.get().strip())
        )
        default_entry.bind(
            "<Return>",
            lambda _e, w=workspace_name, v=default_var: self.save_workspace_setting(w, "default_description", v.get().strip())
        )

        autofill_var = ctk.BooleanVar(value=settings.get("autofill_description", True))
        autofill_check = ctk.CTkCheckBox(
            profile_bubble,
            text="Autofill Description to following parts",
            variable=autofill_var,
            command=lambda w=workspace_name, v=autofill_var: self.save_workspace_setting(w, "autofill_description", v.get())
        )
        autofill_check.pack(anchor="w", padx=15, pady=(2, 10))

        ctk.CTkLabel(profile_bubble, text="Filename / Title Format").pack(anchor="w", padx=15, pady=(3, 2))
        self.build_visual_filename_editor(
            profile_bubble,
            workspace_name,
            settings.get("filename_template", profile["default_filename_template"])
        )

        field_names = ", ".join(field["label"] for field in profile.get("fields", []))
        ctk.CTkLabel(
            profile_bubble,
            text=f"Fields shown in this workspace: {field_names}",
            font=(self.font_family, max(10, self.font_size - 2)),
            text_color="#888888",
            wraplength=700,
            justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 12))

    def get_workspace_settings(self, workspace_name):
        if workspace_name not in WORKSPACES:
            workspace_name = "Accounting"
        all_settings = self.settings.setdefault("workspace_settings", {})
        defaults = DEFAULT_SETTINGS["workspace_settings"][workspace_name]
        current = all_settings.setdefault(workspace_name, copy.deepcopy(defaults))
        for key, value in defaults.items():
            current.setdefault(key, value)
        return current

    def save_workspace_setting(self, workspace_name, key, value):
        settings = self.get_workspace_settings(workspace_name)
        settings[key] = value

        # Keep legacy Accounting keys synchronized.
        if workspace_name == "Accounting":
            if key in {"default_description", "autofill_description", "filename_template"}:
                self.settings[key] = value

        self.save_settings()
        debug(f"{workspace_name} workspace setting saved: {key}={value!r}", "saved")

    def save_workspace_filename_template(self, workspace_name, variable):
        value = variable.get().strip()
        if not value:
            value = WORKSPACES[workspace_name]["default_filename_template"]
            variable.set(value)
        self.save_workspace_setting(workspace_name, "filename_template", value)

    def get_filename_editor_fields(self, workspace_name):
        """Return friendly labels and template tokens for the selected workspace."""
        profile = self.get_workspace_profile(workspace_name)
        fields = [("client", profile.get("client_label", "Client Name"))]

        for field in profile.get("fields", []):
            key = field.get("key")
            if not key:
                continue
            label = field.get("label", key.replace("_", " ").title())
            if key == "date":
                label = "Date"
            fields.append((key, label))

        # Keep the existing Accounting combined token available so previously
        # saved formats display exactly as they did before this visual editor.
        if workspace_name == "Accounting":
            fields.append(("agency_description", "Agency + Description"))

        fields.append(("workspace", "Workspace Name"))
        return fields

    def get_filename_token_label(self, workspace_name, token):
        for field_token, label in self.get_filename_editor_fields(workspace_name):
            if field_token == token:
                return label
        return token.replace("_", " ").title()

    def _filename_editor_colors(self):
        mode = ctk.get_appearance_mode()
        theme = ctk.ThemeManager.theme

        def resolve(value, fallback):
            if value is None:
                return fallback
            if isinstance(value, (list, tuple)):
                return value[0] if mode == "Light" else value[1]
            return value

        editor_bg = resolve(
            theme.get("CTkEntry", {}).get("fg_color"),
            "#ffffff" if mode == "Light" else "#2b2b2b"
        )
        editor_fg = resolve(
            theme.get("CTkEntry", {}).get("text_color"),
            "#111111" if mode == "Light" else "#ffffff"
        )
        token_bg = resolve(
            theme.get("CTkButton", {}).get("fg_color"),
            "#3B8ED0"
        )
        token_fg = resolve(
            theme.get("CTkButton", {}).get("text_color"),
            "#ffffff"
        )
        return editor_bg, editor_fg, token_bg, token_fg

    def build_visual_filename_editor(self, parent, workspace_name, template):
        """Build a mixed free-text + draggable-field filename format editor."""
        editor_bg, editor_fg, token_bg, token_fg = self._filename_editor_colors()

        ctk.CTkLabel(
            parent,
            text=(
                "Type punctuation or words normally. Choose a field below, then drag its block "
                "into the format box (or click Insert Field)."
            ),
            font=(self.font_family, max(10, self.font_size - 2)),
            text_color="#888888",
            wraplength=700,
            justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 6))

        editor = tk.Text(
            parent,
            height=3,
            wrap="word",
            undo=True,
            bg=editor_bg,
            fg=editor_fg,
            insertbackground=editor_fg,
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=8,
            font=(self.font_family, self.font_size)
        )
        editor.pack(fill="x", padx=15, pady=(0, 8))
        editor._filename_token_map = {}
        editor._filename_save_after_id = None

        # Windows filenames cannot contain: < > : " / \ | ? *
        # Block those characters while typing and sanitize pasted text.
        editor.bind(
            "<KeyPress>",
            self._filename_editor_key_filter,
            add="+"
        )
        editor.bind(
            "<<Paste>>",
            lambda _e, box=editor: self._filename_editor_paste(box)
        )

        preview_var = tk.StringVar()

        controls = ctk.CTkFrame(parent, fg_color="transparent")
        controls.pack(fill="x", padx=15, pady=(0, 7))

        field_pairs = self.get_filename_editor_fields(workspace_name)
        label_to_token = {label: token for token, label in field_pairs}
        field_labels = [label for _token, label in field_pairs]
        selected_field = ctk.StringVar(value=field_labels[0] if field_labels else "")

        field_menu = ctk.CTkOptionMenu(
            controls,
            values=field_labels,
            variable=selected_field,
            width=190
        )
        field_menu.pack(side="left", padx=(0, 8))

        drag_chip = tk.Label(
            controls,
            text=f"  {selected_field.get()}  ",
            bg=token_bg,
            fg=token_fg,
            relief="raised",
            borderwidth=1,
            padx=5,
            pady=4,
            cursor="fleur",
            font=(self.font_family, max(10, self.font_size - 1))
        )
        drag_chip.pack(side="left", padx=(0, 8))

        def update_drag_chip(*_):
            drag_chip.configure(text=f"  {selected_field.get()}  ")

        selected_field.trace_add("write", update_drag_chip)

        def insert_selected(index="insert"):
            token = label_to_token.get(selected_field.get())
            if not token:
                return
            self.insert_filename_editor_token(
                editor,
                workspace_name,
                token,
                index,
                preview_var
            )

        ctk.CTkButton(
            controls,
            text="Insert Field",
            width=105,
            command=insert_selected
        ).pack(side="left")

        def drop_selected(event):
            token = label_to_token.get(selected_field.get())
            if not token:
                return

            left = editor.winfo_rootx()
            top = editor.winfo_rooty()
            right = left + editor.winfo_width()
            bottom = top + editor.winfo_height()

            if left <= event.x_root <= right and top <= event.y_root <= bottom:
                x = event.x_root - left
                y = event.y_root - top
                index = editor.index(f"@{x},{y}")
                self.insert_filename_editor_token(
                    editor,
                    workspace_name,
                    token,
                    index,
                    preview_var
                )

        drag_chip.bind("<ButtonRelease-1>", drop_selected)
        drag_chip.bind("<Double-Button-1>", lambda _e: insert_selected())

        self.populate_filename_editor(editor, workspace_name, template, preview_var)

        def on_modified(_event=None):
            try:
                if not editor.edit_modified():
                    return
                editor.edit_modified(False)
            except tk.TclError:
                return
            self.schedule_filename_editor_save(workspace_name, editor, preview_var)

        editor.bind("<<Modified>>", on_modified)
        editor.bind(
            "<FocusOut>",
            lambda _e: self.save_visual_filename_template(workspace_name, editor, preview_var)
        )
        editor.bind(
            "<Return>",
            lambda _e: (
                self.save_visual_filename_template(workspace_name, editor, preview_var),
                "break"
            )[1]
        )
        editor.edit_modified(False)

        ctk.CTkLabel(
            parent,
            text="Preview:",
            font=(self.font_family, max(10, self.font_size - 2), "bold")
        ).pack(anchor="w", padx=15, pady=(1, 0))

        ctk.CTkLabel(
            parent,
            textvariable=preview_var,
            font=(self.font_family, max(10, self.font_size - 2)),
            text_color="#888888",
            wraplength=700,
            justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 10))

        self.update_filename_editor_preview(editor, workspace_name, preview_var)

    def populate_filename_editor(self, editor, workspace_name, template, preview_var):
        editor.delete("1.0", "end")
        editor._filename_token_map.clear()

        position = 0
        for match in re.finditer(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", template):
            if match.start() > position:
                editor.insert("end", template[position:match.start()])
            self.insert_filename_editor_token(
                editor,
                workspace_name,
                match.group(1),
                "end",
                preview_var,
                save=False
            )
            position = match.end()

        if position < len(template):
            editor.insert("end", template[position:])

        editor.edit_modified(False)

    def insert_filename_editor_token(self, editor, workspace_name, token, index, preview_var, save=True):
        try:
            editor_bg, _editor_fg, token_bg, token_fg = self._filename_editor_colors()
            label_text = self.get_filename_token_label(workspace_name, token)

            token_frame = tk.Frame(editor, bg=editor_bg, bd=0, highlightthickness=0)
            token_label = tk.Label(
                token_frame,
                text=label_text,
                bg=token_bg,
                fg=token_fg,
                padx=7,
                pady=2,
                cursor="fleur",
                font=(self.font_family, max(10, self.font_size - 1))
            )
            token_label.pack(side="left")

            remove_button = tk.Label(
                token_frame,
                text=" × ",
                bg=token_bg,
                fg=token_fg,
                cursor="hand2",
                font=(self.font_family, max(10, self.font_size - 1), "bold")
            )
            remove_button.pack(side="left")

            editor.window_create(index, window=token_frame, padx=2, pady=1)
            editor._filename_token_map[str(token_frame)] = token

            def remove_token(_event=None):
                try:
                    token_index = editor.index(str(token_frame))
                    editor.delete(token_index)
                except tk.TclError:
                    pass
                editor._filename_token_map.pop(str(token_frame), None)
                try:
                    token_frame.destroy()
                except tk.TclError:
                    pass
                self.schedule_filename_editor_save(workspace_name, editor, preview_var)

            remove_button.bind("<Button-1>", remove_token)

            drag_state = {
                "start_x": 0,
                "start_y": 0,
                "dragging": False
            }

            def token_press(event):
                drag_state["start_x"] = event.x_root
                drag_state["start_y"] = event.y_root
                drag_state["dragging"] = False
                return "break"

            def token_motion(event):
                dx = abs(event.x_root - drag_state["start_x"])
                dy = abs(event.y_root - drag_state["start_y"])

                # A normal click should not move the field block.
                if dx > 6 or dy > 6:
                    drag_state["dragging"] = True

                return "break"

            def token_release(event):
                if not drag_state["dragging"]:
                    return "break"

                left = editor.winfo_rootx()
                top = editor.winfo_rooty()
                right = left + editor.winfo_width()
                bottom = top + editor.winfo_height()

                if not (
                    left <= event.x_root <= right
                    and top <= event.y_root <= bottom
                ):
                    return "break"

                try:
                    x = event.x_root - left
                    y = event.y_root - top

                    # Preserve the drop position while the original embedded
                    # widget is removed from the Text control.
                    target_index = editor.index(f"@{x},{y}")
                    editor.mark_set("_filename_drop", target_index)
                    editor.mark_gravity("_filename_drop", "right")

                    old_index = editor.index(str(token_frame))
                    editor.delete(old_index)
                    editor._filename_token_map.pop(str(token_frame), None)

                    try:
                        token_frame.destroy()
                    except tk.TclError:
                        pass

                    new_index = editor.index("_filename_drop")
                    editor.mark_unset("_filename_drop")

                    self.insert_filename_editor_token(
                        editor,
                        workspace_name,
                        token,
                        new_index,
                        preview_var
                    )
                except tk.TclError:
                    pass

                return "break"

            token_label.bind("<ButtonPress-1>", token_press)
            token_label.bind("<B1-Motion>", token_motion)
            token_label.bind("<ButtonRelease-1>", token_release)

            if save:
                self.schedule_filename_editor_save(workspace_name, editor, preview_var)
        except tk.TclError:
            return

    def _filename_editor_key_filter(self, event):
        """Prevent characters Windows does not allow in filenames."""
        invalid_chars = '<>:"/\\|?*'

        if event.char and event.char in invalid_chars:
            self.bell()
            return "break"

        # Keep the format on one line even though the editor is a Text widget.
        if event.keysym in ("Return", "KP_Enter"):
            self.bell()
            return "break"

        # Windows filenames cannot contain ASCII control characters.
        if event.char and ord(event.char) < 32 and event.keysym not in (
            "BackSpace", "Delete", "Left", "Right", "Up", "Down",
            "Home", "End", "Tab"
        ):
            # Let modifier shortcuts such as Ctrl+C/Ctrl+V continue normally.
            if not (event.state & 0x0004):
                self.bell()
                return "break"

    def _filename_editor_paste(self, editor):
        """Paste filename text after removing Windows-invalid characters."""
        try:
            text = self.clipboard_get()
        except tk.TclError:
            return "break"

        invalid_chars = '<>:"/\\|?*'
        cleaned = "".join(
            char
            for char in text
            if char not in invalid_chars
            and char not in "\r\n\t"
            and ord(char) >= 32
        )

        try:
            if editor.tag_ranges("sel"):
                editor.delete("sel.first", "sel.last")
            editor.insert("insert", cleaned)
        except tk.TclError:
            return "break"

        if cleaned != text:
            self.bell()

        return "break"

    def serialize_filename_editor(self, editor):
        parts = []
        try:
            for kind, value, _index in editor.dump("1.0", "end-1c", text=True, window=True):
                if kind == "text":
                    parts.append(value)
                elif kind == "window":
                    token = editor._filename_token_map.get(value)
                    if token:
                        parts.append("{" + token + "}")
        except tk.TclError:
            return ""
        return "".join(parts)

    def filename_preview_values(self, workspace_name):
        values = {
            "client": "Smith, John",
            "workspace": workspace_name,
            "revoked": "Revoked",
            "agency": "IRS",
            "description": "POA",
            "agency_description": "IRS POA",
            "date": "8-19-2026",
            "matter_number": "24-0152",
            "document_type": "Notice"
        }
        if workspace_name == "Legal":
            values["client"] = "Smith Matter"
            values["description"] = "Hearing"
        return values

    def update_filename_editor_preview(self, editor, workspace_name, preview_var):
        template = self.serialize_filename_editor(editor)
        if not template:
            template = WORKSPACES[workspace_name]["default_filename_template"]
        try:
            preview = self._format_workspace_filename(
                template,
                self.filename_preview_values(workspace_name),
                workspace_name
            )
            preview_var.set(f"{preview}.pdf")
        except Exception:
            preview_var.set("Unable to preview this format")

    def schedule_filename_editor_save(self, workspace_name, editor, preview_var):
        try:
            pending = getattr(editor, "_filename_save_after_id", None)
            if pending:
                editor.after_cancel(pending)
            editor._filename_save_after_id = editor.after(
                300,
                lambda: self.save_visual_filename_template(workspace_name, editor, preview_var)
            )
        except tk.TclError:
            return

    def save_visual_filename_template(self, workspace_name, editor, preview_var):
        try:
            if not editor.winfo_exists():
                return
        except tk.TclError:
            return

        template = self.serialize_filename_editor(editor).strip()

        # Final guard for text inserted by any route other than typing/paste.
        # Token braces are intentionally preserved because they are valid here.
        template = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '', template)
        template = template.replace("\r", "").replace("\n", "").replace("\t", " ")

        if not template:
            template = WORKSPACES[workspace_name]["default_filename_template"]
            self.populate_filename_editor(editor, workspace_name, template, preview_var)

        self.save_workspace_setting(workspace_name, "filename_template", template)
        self.update_filename_editor_preview(editor, workspace_name, preview_var)
        editor._filename_save_after_id = None

    def _build_license_section(self, parent):
        font = (self.font_family, self.font_size)
        bubble_color, border_color = self.get_log_bubble_colors()

        license_bubble = ctk.CTkFrame(parent, fg_color=bubble_color, border_color=border_color, border_width=2, corner_radius=10)
        license_bubble.pack(padx=10, pady=20, fill="x")

        ctk.CTkLabel(license_bubble, text="🔐 License Info", font=(self.font_family, self.font_size + 2, "bold")).pack(anchor="w", padx=15, pady=(10, 5))

        license_key = ""
        company = self.licensed_company or "Unknown"
        masked = tk.BooleanVar(value=True)

        if LICENSE_FILE.exists():
            try:
                with open(LICENSE_FILE, "r") as f:
                    saved = json.load(f)
                    license_key = saved.get("license_key", "")
            except Exception as e:
                messagebox.showerror("License Error", "License file not found.")
                debug(f"Error reading license file: {e}", "error")

        def get_display_key():
            return "• " * len(license_key) if masked.get() else license_key or "N/A"

        key_var = tk.StringVar(value=get_display_key())

        row = ctk.CTkFrame(license_bubble, fg_color="transparent")
        row.pack(pady=5, padx=15, anchor="w")

        ctk.CTkLabel(row, text="License Key:", font=font, width=120).pack(side="left", padx=(0, 5))
        key_label = ctk.CTkLabel(row, textvariable=key_var, font=font)
        key_label.pack(side="left", padx=(0, 5))

        toggle_btn = ctk.CTkButton(row, text="Show" if masked.get() else "Hide", width=60,
                                   command=lambda: (masked.set(not masked.get()),
                                                    key_var.set(get_display_key()),
                                                    toggle_btn.configure(text="Show" if masked.get() else "Hide")))
        toggle_btn.pack(side="left")

        ctk.CTkLabel(license_bubble, text=f"Company: {company}", font=font).pack(anchor="w", padx=15, pady=(10, 0))
        ctk.CTkLabel(license_bubble, text="Status: ✅ Active", font=font, text_color="#32cd32").pack(anchor="w", padx=15)

        ctk.CTkButton(
            license_bubble,
            text="🧹 Clear License Key",
            fg_color="#cc4b4b",
            hover_color="#aa2b2b",
            text_color="#ffffff",
            command=self.clear_license_and_exit
        ).pack(pady=(20, 10), padx=15, anchor="w")

    # ─── UI Update Helpers ───
    def _apply_font_to_widget(self, widget, font):
        try:
            if not widget.winfo_exists():
                return

            try:
                widget.configure(font=font)
            except Exception:
                pass

            for child in widget.winfo_children():
                self._apply_font_to_widget(child, font)

        except tk.TclError:
            return
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
                try:
                    if session["parts_frame"].winfo_exists():
                        self._apply_font_to_widget(session["parts_frame"], font)
                except tk.TclError:
                    pass
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
        start = time.perf_counter()

        theme_config = THEMES.get(selected_name)
        if theme_config:
            self.show_fullscreen_loading_overlay()

            self.after(50, lambda: self._apply_theme_and_rebuild_with_timer(selected_name, theme_config, start))
    def _apply_theme_and_rebuild_with_timer(self, selected_name, theme_config, start_time):
        ctk.set_appearance_mode(theme_config["mode"])
        ctk.set_default_color_theme(theme_config["theme"])

        self.settings["theme"] = selected_name
        self.theme = selected_name
        self.save_settings()

        self.rebuild_ui()
        self.theme_var.set(selected_name)

        self.after(300, lambda: self._finish_theme_timer(start_time))
    def _finish_theme_timer(self, start_time):
        end = time.perf_counter()
        duration = round(end - start_time, 2)
        print(f"[DEBUG] Theme switch took {duration} seconds")
        self.hide_loading_overlay()
    def reset_ui(self):
        confirm = messagebox.askyesno("Reset Form", "Are you sure you want to clear this form?")
        if not confirm:
            return

        session = self.get_active_session()
        if not session:
            messagebox.showerror("Reset Error", "No active session to reset.")
            return

        workspace_name = session.get("workspace", "Accounting")
        profile = self.get_workspace_profile(workspace_name)
        field_map = {field["key"]: field for field in profile.get("fields", [])}

        self.suppress_autofill = True
        try:
            for entry in session.get("entries", []):
                for key, variable in entry.get("field_vars", {}).items():
                    field = field_map.get(key, {"key": key, "type": "text", "default": ""})
                    variable.set(self.get_workspace_field_default(workspace_name, field))
            session["client_name_var"].set("")
        finally:
            self.suppress_autofill = False

        self.capture_workspace_data(session)
        messagebox.showinfo("Form Reset", f"The {workspace_name} form has been cleared.")
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
        tooltip.attributes("-topmost", True)
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

        widget.bind("<Enter>", on_enter, add="+")
        widget.bind("<Leave>", on_leave, add="+")

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
    def get_workspace_profile(self, workspace_name):
        return WORKSPACES.get(workspace_name, WORKSPACES["Accounting"])

    def get_workspace_field_default(self, workspace_name, field):
        if field.get("key") == "description":
            return self.get_workspace_settings(workspace_name).get("default_description", field.get("default", ""))
        return field.get("default", False if field.get("type") == "bool" else "")

    def capture_workspace_data(self, session):
        workspace_name = session.get("workspace", "Accounting")
        entries = session.get("entries", [])
        if not entries:
            return

        rows = []
        for entry in entries:
            row = {"range": copy.deepcopy(entry["range"])}
            for key, variable in entry.get("field_vars", {}).items():
                try:
                    row[key] = variable.get()
                except Exception:
                    pass
            rows.append(row)

        session.setdefault("workspace_data", {})[workspace_name] = rows

    def change_session_workspace(self, session, workspace_name):
        if workspace_name not in WORKSPACES:
            return
        current = session.get("workspace", "Accounting")
        if current == workspace_name:
            return

        self.capture_workspace_data(session)
        session["workspace"] = workspace_name
        self.settings["default_workspace"] = workspace_name
        self.save_settings()
        debug(f"Workspace switched: {current} -> {workspace_name}", "debug")
        self.render_splitter_tab(session["tab"], session)
        self.save_sessions()

    def get_workspace_saved_value(self, session, workspace_name, part_index, field, default):
        rows = session.get("workspace_data", {}).get(workspace_name, [])
        if part_index < len(rows):
            return rows[part_index].get(field, default)
        return default

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

            skipped_pages = []

            for i, r in enumerate(ranges, start=1):
                writer = PdfWriter()
                for p in range(r["start"], r["end"] + 1):
                    page = reader.pages[p]
                    if self.settings.get("remove_blank_pages", True) and self.is_blank_page(page):
                        skipped_pages.append(p + 1)
                        continue
                    writer.add_page(page)

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
    def update_future_date_setting(self):
        suppress = not self.future_date_popup_var.get()
        self.settings["suppressFutureDateWarning"] = suppress
        self.save_settings()

    def save_setting(self, key, value):
        self.settings[key] = value
        self.save_settings()

    def update_autofill_description_setting(self):
        value = self.autofill_description_var.get() if hasattr(self, "autofill_description_var") else True
        self.save_workspace_setting("Accounting", "autofill_description", value)
    def update_default_description_setting(self, event=None):
        value = self.default_description_var.get().strip() if hasattr(self, "default_description_var") else "POA"
        self.save_workspace_setting("Accounting", "default_description", value)
    def update_filename_template_setting(self):
        value = self.filename_template_var.get().strip() if hasattr(self, "filename_template_var") else ""
        if not value:
            value = WORKSPACES["Accounting"]["default_filename_template"]
            if hasattr(self, "filename_template_var"):
                self.filename_template_var.set(value)
        self.save_workspace_setting("Accounting", "filename_template", value)
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

            bubble_color, border_color = self.get_log_bubble_colors()

            container = ctk.CTkFrame(
                self.log_scroll_frame,
                fg_color=bubble_color,
                border_color=border_color,
                border_width=3,
                corner_radius=5
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

                default_text_color = "#dddddd" if ctk.get_appearance_mode() == "Dark" else "#222222"

                ctk.CTkLabel(
                    container,
                    text=clean,
                    anchor="w",
                    wraplength=820,
                    justify="left",
                    text_color=default_text_color,
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
            entry = CTkEntry(scrollable, textvariable=var)
            entry.pack(pady=2, fill="x")
            return var

        filters["client"] = make_entry("Client Name (partial ok)")
        filters["agency"] = make_entry("Agency Code (e.g., IRS, FTB)")
        filters["export_date"] = make_entry("Export Date (YYYY-MM-DD)")
        filters["part_date"] = make_entry("Part Date (MM-DD-YY)")

        ctk.CTkLabel(scrollable, text="Export Format", font=font).pack(pady=(10, 0))
        format_var = tk.StringVar(value="CSV")
        ctk.CTkOptionMenu(scrollable, values=["CSV", "TSV", "TXT", "PDF", "Print"], variable=format_var).pack()

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
            if not line.strip() or "Client:" not in line:
                continue

            client = self._extract_value(line, "Client")
            agency = self._extract_value(line, "Agency")
            part_date = self._extract_value(line, "Date")
            revoked = self._extract_value(line, "Revoked")
            desc = self._extract_value(line, "Desc")
            file = self._extract_value(line, "File")
            skipped = self._extract_value(line, "Skipped")
            pages = self._extract_value(line, "Pages")

            timestamp_match = re.match(r"\[(.*?)\]", line)
            export_date = timestamp_match.group(1).split()[0] if timestamp_match else ""

            if query_client and query_client not in client:
                continue
            if query_agency and query_agency not in agency:
                continue
            if query_export_date and query_export_date not in export_date:
                continue
            if query_part_date and query_part_date not in part_date:
                continue

            pages_wrapped = f'="{pages}"' if pages else ""

            matches.append({
                "Export Date": export_date,
                "Client": client,
                "File": file,
                "Pages": pages_wrapped,
                "Skipped": skipped,
                "Agency": agency,
                "Desc": desc,
                "Date": part_date,
                "Revoked": revoked
            })

        if not matches:
            messagebox.showinfo("No Matches", "No log entries matched your filters.")
            return

        # Export actions
        if export_format == "CSV":
            file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
            if not file_path:
                return
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=matches[0].keys())
                writer.writeheader()
                writer.writerows(matches)
            messagebox.showinfo("Exported", f"{len(matches)} log entries saved to:\n{file_path}")

        elif export_format == "TSV":
            file_path = filedialog.asksaveasfilename(defaultextension=".tsv", filetypes=[("TSV files", "*.tsv")])
            if not file_path:
                return
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=matches[0].keys(), delimiter="\t")
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

        elif export_format == "PDF":
            try:
                from reportlab.lib.pagesizes import LETTER
                from reportlab.pdfgen import canvas
            except ImportError:
                messagebox.showerror("Missing Library", "The 'reportlab' package is required for PDF export.\nInstall it using: pip install reportlab")
                return

            file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
            if not file_path:
                return

            try:
                c = canvas.Canvas(file_path, pagesize=LETTER)
                width, height = LETTER
                y = height - 40
                c.setFont("Helvetica", 10)

                for entry in matches:
                    line = " | ".join(f"{k}: {v}" for k, v in entry.items())
                    c.drawString(40, y, line)
                    y -= 15
                    if y < 40:
                        c.showPage()
                        y = height - 40
                        c.setFont("Helvetica", 10)

                c.save()
                messagebox.showinfo("Exported", f"{len(matches)} log entries saved to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to generate PDF:\n{e}")

        elif export_format == "Print":
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
    def get_log_bubble_colors(self):
        theme_name = self.settings.get("theme", "Light Blue")

        colors = {
            "Light Blue":  ("#cbd3d9", "#3b8ed0"),
            "Dark Blue":   ("#1f2b3a", "#3a506b"),
            "Dark Green":  ("#1e2f1e", "#3b5f3b"),
            "Light Pink":  ("#f7d6e0", "#f2eaf7"),
            "Dark Pink":   ("#3e3336", "#ff8fb3")
        }

        return colors.get(theme_name, ("#f0f0f0", "#cccccc"))

    # ─── PDF Load & Split ───
    def load_pdf(self):
        paths = filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
        for path in paths:
            if path.lower().endswith(".pdf"):
                self.load_pdf_from_path(path)
    def load_pdf_from_path(self, path, render=True):
        pdf_name = Path(path).stem

        # Prevent duplicate loads
        if pdf_name in self.pdf_sessions:
            messagebox.showinfo("Already Loaded", f"{pdf_name} is already open.")
            return

        try:
            reader = PdfReader(path)
            ranges = self.detect_split_ranges_from_reader(reader)

            pdf_name = Path(path).stem
            tab_label = f"{pdf_name} ✖"
            tab = self.pdf_tabview.add(tab_label)
            self._apply_tab_font_size()
            self.pdf_tabview.set(tab_label)

            session = {
                "tab": tab,
                "tab_label": tab_label,
                "reader": reader,
                "path": Path(path),
                "ranges": ranges,
                "entries": [],
                "client_name_var": ctk.StringVar(),
                "workspace": self.settings.get("default_workspace", "Accounting"),
                "workspace_data": {},
                "last_exported_files": [],
                "widgets_to_scale": []
            }

            self.pdf_sessions[pdf_name] = session

            self.update_idletasks()
            self.render_splitter_tab(tab, session)

            self.enable_tab_closing()

            if (
                not self.settings.get("tutorial_shown", False)
                and not self.tutorial_cancelled_this_session
                and not self.tutorial_active
                and not self.tutorial_pending
            ):
                self.tutorial_pending = True
                self.after(250, self.start_tutorial)

        except Exception as e:
            messagebox.showerror("Error", str(e))
            debug(f"Error Loading PDF: {e}", "error")
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
        prev_val = {"last": var.get()}

        def handler(*_):
            if self.suppress_autofill:
                prev_val["last"] = var.get()
                return

            value = var.get()
            previous_source_value = prev_val["last"]
            debug(
                f"Autofill triggered on part {index + 1} for '{field}' with value: '{value}'",
                "debug"
            )

            for j in range(index + 1, len(entries_ref)):
                current_val = entries_ref[j][field].get()

                # Only update a later field while it still matches the value that
                # was previously propagated. Once a user edits it manually, leave it alone.
                should_update = current_val == previous_source_value

                # String fields also propagate naturally while typing forward.
                if isinstance(value, str) and isinstance(current_val, str):
                    if current_val == value[:-1]:
                        should_update = True

                if should_update:
                    entries_ref[j][field].set(value)
                    debug(f"→ Autofilled Part {j + 1} '{field}' with '{value}'", "debug")
                else:
                    debug(
                        f"→ Left Part {j + 1} '{field}' unchanged (manual value: '{current_val}')",
                        "skip"
                    )

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

            base_name = "_".join(parts)
            fname = base_name + ".pdf"
            file_path = out_dir / fname

            # Ensure uniqueness
            counter = 1
            while file_path.exists():
                fname = f"{base_name}_{counter}.pdf"
                file_path = out_dir / fname
                counter += 1

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
        self.export_active_session()
    def render_splitter_tab(self, tab_frame, session):
        for widget in tab_frame.winfo_children():
            widget.destroy()

        session["entries"] = []
        session["widgets_to_scale"] = []
        ranges = session["ranges"]

        workspace_name = session.get("workspace", self.settings.get("default_workspace", "Accounting"))
        if workspace_name not in WORKSPACES:
            workspace_name = "Accounting"
        session["workspace"] = workspace_name
        profile = self.get_workspace_profile(workspace_name)
        workspace_settings = self.get_workspace_settings(workspace_name)

        bubble_color, border_color = self.get_log_bubble_colors()

        bubble = ctk.CTkFrame(
            tab_frame,
            fg_color=bubble_color,
            border_color=border_color,
            border_width=3,
            corner_radius=10
        )
        bubble.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            bubble,
            text="🧩 Split & Rename",
            font=(self.font_family, self.font_size + 4, "bold"),
            text_color="#3B8ED0"
        ).pack(pady=(10, 4))

        workspace_row = ctk.CTkFrame(bubble, fg_color="transparent")
        workspace_row.pack(pady=(0, 4))
        workspace_label = ctk.CTkLabel(
            workspace_row,
            text="Workspace:",
            font=(self.font_family, self.font_size, "bold")
        )
        workspace_label.pack(side="left", padx=(0, 8))
        session["workspace_var"] = ctk.StringVar(value=workspace_name)
        workspace_menu = ctk.CTkOptionMenu(
            workspace_row,
            values=list(WORKSPACES.keys()),
            variable=session["workspace_var"],
            command=lambda selected, s=session: self.change_session_workspace(s, selected),
            width=170
        )
        workspace_menu.pack(side="left")
        session["widgets_to_scale"].extend([workspace_label, workspace_menu])

        workspace_summary = ctk.CTkLabel(
            bubble,
            text=profile.get("summary", ""),
            font=(self.font_family, max(10, self.font_size - 2)),
            text_color="#888888",
            wraplength=820,
            justify="center"
        )
        workspace_summary.pack(pady=(0, 6))

        content = ctk.CTkFrame(bubble)
        content.pack(fill="both", expand=True, padx=10, pady=10)

        form_frame = ctk.CTkScrollableFrame(content, width=520)
        form_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        session["parts_frame"] = form_frame

        client_box = ctk.CTkFrame(form_frame, fg_color="transparent")
        client_box.pack(pady=(10, 10), padx=10, anchor="w", fill="x")

        name_label = ctk.CTkLabel(client_box, text=f"{profile.get('client_label', 'Client Name')}:")
        name_label.pack(side="left")
        session["widgets_to_scale"].append(name_label)

        info_icon = ctk.CTkLabel(client_box, text="❓", text_color="#888888", cursor="question_arrow")
        info_icon.pack(side="left", padx=(5, 10))
        self.add_tooltip(
            info_icon,
            "Names use smart title case. Mixed capitalization and common acronyms are preserved."
        )

        name_entry = CTkEntry(client_box, textvariable=session["client_name_var"], width=300)
        name_entry.pack(side="left")
        session["client_name_entry"] = name_entry
        session["widgets_to_scale"].append(name_entry)

        for part_index, r in enumerate(ranges):
            part_number = part_index + 1
            part_card = ctk.CTkFrame(form_frame, fg_color=bubble_color, corner_radius=10)
            part_card.pack(fill="x", padx=10, pady=(0, 10))

            header = ctk.CTkFrame(part_card, fg_color="transparent")
            header.pack(fill="x", pady=(10, 0), padx=10)

            part_title = ctk.CTkLabel(
                header,
                text=f"Part {part_number} — Pages {r['start'] + 1} to {r['end'] + 1}",
                font=(self.font_family, self.font_size + 1, "bold")
            )
            part_title.pack(side="left")
            session["widgets_to_scale"].append(part_title)

            entry = {
                "range": r,
                "field_vars": {},
                "field_widgets": {}
            }
            session["entries"].append(entry)

            # Header controls (Accounting's Revoked switch, for example).
            for field in profile.get("fields", []):
                if field.get("placement") != "header":
                    continue
                key = field["key"]
                default = self.get_workspace_field_default(workspace_name, field)
                saved = self.get_workspace_saved_value(session, workspace_name, part_index, key, default)
                variable = ctk.BooleanVar(value=bool(saved))
                widget = ctk.CTkSwitch(header, text=field["label"], variable=variable)
                widget.pack(side="right")
                entry["field_vars"][key] = variable
                entry["field_widgets"][key] = widget
                entry[key] = variable
                session["widgets_to_scale"].append(widget)

            # Standard fields.
            for field in profile.get("fields", []):
                if field.get("placement") == "header":
                    continue

                key = field["key"]
                default = self.get_workspace_field_default(workspace_name, field)
                saved = self.get_workspace_saved_value(session, workspace_name, part_index, key, default)

                label_row = ctk.CTkFrame(part_card, fg_color="transparent")
                label_row.pack(anchor="w", padx=12, pady=(8, 0), fill="x")
                label = ctk.CTkLabel(label_row, text=field["label"])
                label.pack(side="left")
                session["widgets_to_scale"].append(label)

                tooltip = field.get("tooltip")
                if tooltip:
                    tip_icon = ctk.CTkLabel(label_row, text="❓", text_color="#888888", cursor="question_arrow")
                    tip_icon.pack(side="left", padx=(5, 0))
                    self.add_tooltip(tip_icon, tooltip)
                    session["widgets_to_scale"].append(tip_icon)

                variable = ctk.StringVar(value=str(saved) if saved is not None else "")
                widget = CTkEntry(
                    part_card,
                    textvariable=variable,
                    placeholder_text=field.get("placeholder", "")
                )
                widget.pack(anchor="w", padx=12, fill="x", pady=(0, 5 if key != "date" else 10))

                entry["field_vars"][key] = variable
                entry["field_widgets"][key] = widget
                entry[key] = variable
                entry[f"{key}_entry"] = widget
                session["widgets_to_scale"].append(widget)

            # Attach autofill traces only after this part's variables exist.
            for field in profile.get("fields", []):
                key = field["key"]
                variable = entry["field_vars"].get(key)
                if variable is None or not field.get("autofill", False):
                    continue
                if key == "description" and not workspace_settings.get("autofill_description", True):
                    continue
                variable.trace_add(
                    "write",
                    self.make_autofill_handler(key, variable, part_index, session["entries"])
                )

        preview_frame = ctk.CTkFrame(content, width=520)
        preview_frame.pack_propagate(False)
        preview_frame.pack(side="left", fill="y", padx=10, pady=10)

        ctk.CTkLabel(
            preview_frame,
            text="Preview",
            font=(self.font_family, self.font_size + 1, "bold")
        ).pack(pady=(10, 5))
        self.render_pdf_preview(session, preview_frame)

        make_folder = ctk.CTkCheckBox(bubble, text="Make Client Folder", variable=self.make_client_folder_var)
        make_folder.pack(pady=(5, 0))
        session["widgets_to_scale"].append(make_folder)

        button_row = ctk.CTkFrame(bubble, fg_color="transparent")
        button_row.pack(pady=10)

        ctk.CTkButton(button_row, text="Export PDFs", command=lambda: self.export_session(session)).pack(side="left", padx=10)
        ctk.CTkButton(
            button_row,
            text="Reset Form",
            fg_color="#cc4b4b",
            hover_color="#aa2b2b",
            command=self.reset_ui
        ).pack(side="left", padx=10)
        ctk.CTkButton(button_row, text="Show Keybinds", command=self.open_keybind_overlay).pack(side="left", padx=10)

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
            max_width = 365
            max_height = 650
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
        workspace_name = session.get("workspace", "Accounting")
        profile = self.get_workspace_profile(workspace_name)
        client_name = self.title_case(session["client_name_var"].get().strip())
        if not client_name:
            messagebox.showerror(
                f"Missing {profile.get('client_label', 'Client Name')}",
                f"Please enter {profile.get('client_label', 'Client Name').lower()}."
            )
            return

        missing_dates = []
        for idx, entry in enumerate(session.get("entries", []), start=1):
            date_var = entry.get("field_vars", {}).get("date")
            if date_var is not None and not date_var.get().strip():
                missing_dates.append(str(idx))

        if missing_dates:
            parts_text = ", ".join(missing_dates)
            if not messagebox.askyesno(
                "Missing Date",
                f"Part(s) {parts_text} do not have a date.\n\n"
                "You can still export them; the date will simply be omitted from those filenames.\n\n"
                "Continue exporting?"
            ):
                return

        for idx, entry in enumerate(session.get("entries", []), start=1):
            date_var = entry.get("field_vars", {}).get("date")
            if date_var is None:
                continue
            date_str = date_var.get().strip()
            if not date_str or not re.fullmatch(r"\d{6}", date_str):
                continue

            try:
                today = datetime.date.today()
                normalized = self.format_date(date_str)
                entered_date = datetime.datetime.strptime(normalized, "%m-%d-%Y").date()
                if entered_date > today and not self.settings.get("suppressFutureDateWarning", False):
                    debug(f"Future date found in part {idx}: {date_str}", "debug")
                    self.check_future_date(
                        date_str,
                        callback_on_confirm=lambda: self._finalize_export(session)
                    )
                    return
            except Exception:
                continue

        self._finalize_export(session)
    def get_workspace_export_values(self, session, client_name, entry, formatted_date):
        workspace_name = session.get("workspace", "Accounting")
        profile = self.get_workspace_profile(workspace_name)
        raw = {}
        for key, variable in entry.get("field_vars", {}).items():
            try:
                raw[key] = variable.get()
            except Exception:
                raw[key] = ""

        agency = self.get_agency(str(raw.get("agency", ""))) if "agency" in raw else ""
        description = str(raw.get("description", "")).strip()
        document_type = str(raw.get("document_type", "")).strip()
        matter_number = str(raw.get("matter_number", "")).strip()

        field_map = {field["key"]: field for field in profile.get("fields", [])}
        if field_map.get("description", {}).get("title_case"):
            description = self.title_case(description)
        if field_map.get("document_type", {}).get("title_case"):
            document_type = self.title_case(document_type)

        revoked = bool(raw.get("revoked", False))
        agency_description = " ".join(part for part in (agency, description) if part).strip()

        return {
            "client": client_name,
            "workspace": workspace_name,
            "revoked": "Revoked" if revoked else "",
            "agency": agency,
            "description": description,
            "agency_description": agency_description,
            "date": formatted_date,
            "matter_number": matter_number,
            "document_type": document_type
        }

    def build_filename(self, client_name, revoked=False, agency="", desc="", formatted_date="", workspace_name="Accounting", extra_values=None):
        # Backward-compatible helper; workspace-aware exports use the same token system.
        if workspace_name not in WORKSPACES:
            workspace_name = "Accounting"
        values = {
            "client": client_name,
            "workspace": workspace_name,
            "revoked": "Revoked" if revoked else "",
            "agency": agency,
            "description": desc,
            "agency_description": " ".join(part for part in (agency, desc) if part).strip(),
            "date": formatted_date,
            "matter_number": "",
            "document_type": ""
        }
        if extra_values:
            values.update(extra_values)

        template = self.get_workspace_settings(workspace_name).get(
            "filename_template",
            WORKSPACES[workspace_name]["default_filename_template"]
        )
        return self._format_workspace_filename(template, values, workspace_name)

    def _format_workspace_filename(self, template, values, workspace_name):
        try:
            base_name = template.format(**values)
        except (KeyError, ValueError) as error:
            fallback = WORKSPACES[workspace_name]["default_filename_template"]
            debug(f"Invalid {workspace_name} filename template '{template}': {error}; using default", "warning")
            base_name = fallback.format(**values)

        # Final Windows filename safety pass. The visual editor blocks these
        # characters, but field values can still contain them.
        base_name = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", base_name)
        base_name = re.sub(r"_{2,}", "_", base_name)
        base_name = re.sub(r"\s{2,}", " ", base_name)
        base_name = base_name.strip(" _-")
        base_name = base_name.rstrip(". ")

        # Windows reserves these names even when a file extension is present.
        reserved_names = {
            "CON", "PRN", "AUX", "NUL",
            *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10))
        }
        if base_name.upper() in reserved_names:
            base_name = "_" + base_name

        return base_name or "Document"
    def _finalize_export(self, session):
        debug("Finalizing export...", "debug")

        workspace_name = session.get("workspace", "Accounting")
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
        workspace_settings = self.get_workspace_settings(workspace_name)
        filename_template = workspace_settings.get(
            "filename_template",
            WORKSPACES[workspace_name]["default_filename_template"]
        )

        for idx, entry in enumerate(session.get("entries", []), start=1):
            date_var = entry.get("field_vars", {}).get("date")
            raw_date = date_var.get().strip() if date_var is not None else ""
            if raw_date:
                try:
                    formatted_date = self.format_date(raw_date)
                except ValueError as e:
                    messagebox.showerror("Invalid Date", f"Error in Part {idx}:\n{e}")
                    return
            else:
                formatted_date = ""

            writer = PdfWriter()
            r = entry["range"]
            skipped = []

            for p in range(r["start"], r["end"] + 1):
                page = session["reader"].pages[p]
                if self.settings.get("remove_blank_pages", True) and self.is_blank_page(page):
                    skipped.append(p + 1)
                    continue
                writer.add_page(page)

            values = self.get_workspace_export_values(session, client_name, entry, formatted_date)
            base_name = self._format_workspace_filename(filename_template, values, workspace_name)
            fname = f"{base_name}.pdf"
            file_path = out_dir / fname

            counter = 2
            while file_path.exists():
                fname = f"{base_name}_{counter}.pdf"
                file_path = out_dir / fname
                counter += 1

            with open(file_path, "wb") as f:
                writer.write(f)

            session["last_exported_files"].append(file_path)

            log_lines.append(
                f"Workspace: {workspace_name} | Client: {client_name} | File: {fname} | "
                f"Pages: {r['start']+1}-{r['end']+1} | Skipped: {skipped if skipped else 'None'} | "
                f"Agency: {values['agency']} | Desc: {values['description']} | "
                f"Date: {formatted_date or 'None'} | Revoked: {values['revoked'] == 'Revoked'} | "
                f"Matter: {values['matter_number']} | Document Type: {values['document_type']}"
            )

        self.last_exported_files = list(session["last_exported_files"])

        if self.settings.get("export_log_enabled", True):
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                for line in log_lines:
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"[{timestamp}] {line}\n")
            self.load_full_log()

        messagebox.showinfo(
            "Export Complete",
            f"Exported {len(session['last_exported_files'])} {workspace_name} file(s) to:\n{out_dir}"
        )
        debug(f"Exported {workspace_name} files to: {out_dir}", "debug")

        tab_name = next((name for name, s in self.pdf_sessions.items() if s is session), None)
        if tab_name:
            tab_label = session.get("tab_label", tab_name)
            self.pdf_tabview.delete(tab_label)
            self.pdf_sessions.pop(tab_name, None)
            self.save_sessions()
    def split_paths(self, data):
        # Example: '{C:/file1.pdf} {C:/file2.pdf}'
        return [p.strip("{}") for p in data.strip().split() if p.strip()]
    def add_plus_tab(self):
        if not hasattr(self, "pdf_tabview") or not isinstance(self.pdf_tabview, ctk.CTkTabview):
            return

        existing_tabs = getattr(self.pdf_tabview, "_tabs", {})
        if "+" in existing_tabs:
            return

        plus_tab = self.pdf_tabview.add("➕ New PDF")
        self.pdf_tabview.set("➕ New PDF")

        bubble_color, border_color = self.get_log_bubble_colors()

        # Use pack for more reliable layout and border rendering
        wrapper = ctk.CTkFrame(plus_tab)
        wrapper.pack(fill="both", expand=True)

        bubble = ctk.CTkFrame(
            wrapper,
            fg_color=bubble_color,
            border_color=border_color,
            border_width=2,
            corner_radius=12
        )
        bubble.pack(expand=True, ipadx=20, ipady=20, padx=40, pady=40)

        # Title
        ctk.CTkLabel(
            bubble,
            text="📄 Open a PDF to Begin",
            font=(self.font_family, self.font_size + 4, "bold"),
            text_color="#3B8ED0"
        ).pack(pady=(20, 10))

        # Button
        ctk.CTkButton(
            bubble,
            text="➕ Open PDF",
            command=self.load_pdf,
            width=160
        ).pack(pady=(0, 10))

        # Tip
        ctk.CTkLabel(
            bubble,
            text="Or drag and drop files into this area.",
            font=(self.font_family, self.font_size - 1),
            text_color="#888888"
        ).pack(pady=(0, 20))

        # Enable drag and drop
        wrapper.drop_target_register(DND_FILES)
        wrapper.dnd_bind('<<Drop>>', self.handle_drop)
    def add_plus_tab2(self):
        if not hasattr(self, "pdf_tabview") or not isinstance(self.pdf_tabview, ctk.CTkTabview):
            return

        existing_tabs = getattr(self.pdf_tabview, "_tabs", {})
        if "+" in existing_tabs:
            return

        plus_tab = self.pdf_tabview.add("+")
        self.pdf_tabview.set("+")

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
        import pymupdf as fitz

        out_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")],
            title="Save SPLIT HERE Sheet As",
            initialfile="split_here_sheet.pdf"
        )
        if not out_path:
            return

        try:
            doc = fitz.open()
            page = doc.new_page(width=612, height=792)

            text = "SPLIT HERE"
            font_size = 48
            text_width = fitz.get_text_length(text, fontname="helv", fontsize=font_size)
            x = (612 - text_width) / 2
            y = 396

            page.insert_text(
                (x, y),
                text,
                fontsize=font_size,
                fontname="helv",
                color=(0, 0, 0)
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
            messagebox.showinfo("Preview Page Error", f"Failed to update preview page: {e}")
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
            if not win.winfo_exists() or not canvas.winfo_exists():
                return "break"
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
            if not win.winfo_exists() or not canvas.winfo_exists():
                return "break"
            canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
            debug(f"Shift+Wheel scroll (horizontal): delta={event.delta}", "debug")

        def close_preview(event=None):
            debug("Closing fullscreen preview", "debug")
            try:
                win.unbind("<MouseWheel>")
                win.unbind("<Shift-MouseWheel>")
                win.unbind("<Escape>")
            except tk.TclError:
                pass
            if win.winfo_exists():
                win.destroy()

        # Keep wheel bindings local to this preview window. Using bind_all here
        # leaves callbacks alive after the canvas is destroyed.
        win.bind("<MouseWheel>", _on_mousewheel)
        win.bind("<Shift-MouseWheel>", _on_shiftwheel)
        win.bind("<Escape>", close_preview)
        win.protocol("WM_DELETE_WINDOW", close_preview)

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

            current_year = datetime.date.today().year
            century = current_year // 100 * 100
            two_digit = y

            if two_digit <= (current_year + 70) % 100:
                y = century + two_digit
            else:
                y = century - 100 + two_digit

            date_obj = datetime.date(y, m, d)
            debug(f"Parsed date: {date_obj.isoformat()}", "debug")

        except ValueError:
            raise ValueError("Date contains an invalid month or day (e.g. Feb 30 doesn't exist)")

        return f"{date_obj.month}-{date_obj.day:02d}-{date_obj.year}"
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

    def get_active_session(self):
        if not hasattr(self, "pdf_tabview"):
            return None
        tab_label = self.pdf_tabview.get()
        if tab_label in {"+", "➕ New PDF"}:
            return None
        base_name = tab_label.replace(" ✖", "")
        return self.pdf_sessions.get(base_name)

    def export_active_session(self):
        session = self.get_active_session()
        if not session:
            messagebox.showinfo("Export PDFs", "Open or select a PDF tab first.")
            return
        self.export_session(session)

    def focus_active_client_name(self):
        session = self.get_active_session()
        if session and session.get("client_name_entry"):
            session["client_name_entry"].focus_set()

    def focus_active_first_part(self):
        session = self.get_active_session()
        if not session or not session.get("entries"):
            return
        first = session["entries"][0]
        for widget in first.get("field_widgets", {}).values():
            try:
                widget.focus_set()
                return
            except Exception:
                continue
    def _tk_sequence_for_combo(self, combo):
        if not combo:
            return None

        tokens = [token.strip().lower() for token in combo.split("+") if token.strip()]
        if not tokens:
            return None

        modifier_map = {
            "ctrl": "Control",
            "control": "Control",
            "shift": "Shift",
            "alt": "Alt",
            "option": "Alt"
        }
        key_map = {
            "enter": "Return",
            "return": "Return",
            "esc": "Escape",
            "escape": "Escape",
            "backspace": "BackSpace",
            "delete": "Delete",
            "space": "space",
            "tab": "Tab"
        }

        modifiers = []
        key = None
        for token in tokens:
            if token in modifier_map:
                mod = modifier_map[token]
                if mod not in modifiers:
                    modifiers.append(mod)
            else:
                key = key_map.get(token, token)

        if not key:
            return None

        ordered = [m for m in ("Control", "Alt", "Shift") if m in modifiers]
        if "Shift" in ordered and len(key) == 1 and key.isalpha():
            key = key.upper()
        return "<" + "-".join(ordered + [key]) + ">"

    def save_keybinds(self, show_message=True):
        self.keybindings = {action: var.get() for action, var in self.keybind_vars.items()}
        with open(KEYBINDS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.keybindings, f, indent=2)
        debug(f"Keybinds written to file: {self.keybindings}", "keybind")
        self.apply_keybinds()
        if show_message:
            messagebox.showinfo("Keybinds Updated", "New keybindings have been saved.")

    def apply_keybinds(self):
        debug("Applying Tkinter keybinds", "keybind")

        for sequence in getattr(self, "_bound_key_sequences", []):
            try:
                self.unbind_all(sequence)
            except tk.TclError:
                pass
        self._bound_key_sequences = []

        for action, combo in self.keybindings.items():
            sequence = self._tk_sequence_for_combo(combo)
            if not sequence:
                debug(f"Skipped invalid keybind: {action} -> {combo}", "warning")
                continue

            callback = self.get_action_callback(action)

            def handler(event=None, action_name=action, cb=callback):
                if self.setting_keybind:
                    return "break"
                self._run_if_focused(action_name, cb)
                return "break"

            try:
                self.bind_all(sequence, handler)
                self._bound_key_sequences.append(sequence)
                debug(f"Keybind added: {action} -> {sequence}", "keybind")
            except tk.TclError as error:
                debug(f"Failed to bind {combo}: {error}", "error")

        # Keep the debug console shortcut internal and reliable.
        self.bind_all("<Control-Alt-d>", lambda _e: (self.open_debug_console(), "break")[1])
        self._bound_key_sequences.append("<Control-Alt-d>")

    def undo_last_export(self):
        debug("Undo keybind triggered", "undo")
        debug(f"Files pending undo: {self.last_exported_files}", "undo")

        if not self.last_exported_files:
            messagebox.showinfo("Undo", "No export to undo.")
            return

        confirm = messagebox.askyesno(
            title="Confirm Undo",
            message="Are you sure you want to permanently delete the most recent export?\n\nThis cannot be undone."
        )
        if not confirm:
            return

        deleted = 0
        for path in list(self.last_exported_files):
            try:
                if path.exists():
                    path.unlink()
                    deleted += 1
                    if path.parent.exists() and not any(path.parent.iterdir()):
                        path.parent.rmdir()
            except Exception as e:
                messagebox.showwarning("Undo Failed", f"Could not delete: {path.name}\n{e}")
                debug(f"Failed to delete {path}: {e}", "error")

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            if deleted > 0:
                for path in self.last_exported_files:
                    f.write(f"[{timestamp}] Undo: Deleted '{path.name}' from '{path.parent}'\n")
                self.last_exported_files = []
                debug(f"Undo complete: {deleted} file(s) deleted", "undo")
            else:
                f.write(f"[{timestamp}] Undo attempted, but no files were deleted.\n")

        self.load_full_log()

    def start_keybind_input(self, action, label_widget):
        if self.setting_keybind:
            return

        debug(f"Starting keybind input for: {action}", "keybind")
        self.setting_keybind = True
        self.active_keybind_target = action
        original_combo = self.keybindings.get(action, "")
        self.keybind_vars[action].set("Press key combo...")

        def finish_capture(combo=None):
            if self._key_capture_bind_id:
                try:
                    self.unbind("<KeyPress>", self._key_capture_bind_id)
                except tk.TclError:
                    pass
                self._key_capture_bind_id = None

            self.setting_keybind = False
            self.active_keybind_target = None

            if combo:
                self.keybind_vars[action].set(combo)
                self.keybindings[action] = combo
                self.save_keybinds(show_message=False)
                debug(f"Captured keybind for {action}: {combo}", "keybind")
            else:
                self.keybind_vars[action].set(original_combo)
                self.apply_keybinds()

        def on_keypress(event):
            pure_modifiers = {
                "Control_L", "Control_R", "Shift_L", "Shift_R",
                "Alt_L", "Alt_R", "Meta_L", "Meta_R"
            }
            if event.keysym in pure_modifiers:
                return
            if event.keysym == "Escape":
                finish_capture(None)
                return "break"

            parts = []
            if event.state & 0x0004:
                parts.append("ctrl")
            if event.state & 0x0008 or event.state & 0x20000:
                parts.append("alt")
            if event.state & 0x0001:
                parts.append("shift")

            key = event.keysym.lower()
            key_names = {
                "return": "enter",
                "escape": "esc",
                "backspace": "backspace",
                "delete": "delete",
                "space": "space",
                "tab": "tab"
            }
            key = key_names.get(key, key)
            parts.append(key)
            finish_capture("+".join(parts))
            return "break"

        self._key_capture_bind_id = self.bind("<KeyPress>", on_keypress, add="+")
        self.focus_force()

    def get_action_callback(self, action):
        return {
            "Open PDF": self.load_pdf,
            "Export PDFs": self.export_active_session,
            "Reset": self.reset_ui,
            "Quit": self._on_close,
            "Search Logs": self.focus_search,
            "Undo Last Export": self.undo_last_export,
            "Paste Clipboard": self.paste_clipboard,
            "Clear Log": self.clear_log,
            "Close Tab": self.close_current_tab,
            "Focus Client Name": self.focus_active_client_name,
            "Focus First Part": self.focus_active_first_part,
            "Select Export Folder": self.set_export_folder
        }.get(action, lambda: None)

    def unbind_all_keys(self):
        for sequence in getattr(self, "_bound_key_sequences", []):
            try:
                self.unbind_all(sequence)
            except tk.TclError:
                pass
        self._bound_key_sequences = []

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
        if tab_label in {"+", "➕ New PDF"}:
            debug("Clicked new-PDF tab — ignoring close zone", "debug")
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
        tab_label = self.pdf_tabview.get()
        if tab_label in {"+", "➕ New PDF"}:
            return

        base_name = tab_label.replace(" ✖", "")
        confirm = messagebox.askyesno("Close Tab", f"Close '{base_name}'?")
        if not confirm:
            return

        self.pdf_tabview.delete(tab_label)

        if base_name in self.pdf_sessions:
            del self.pdf_sessions[base_name]
            debug(f"Session '{base_name}' removed from pdf_sessions", "debug")
            self.save_sessions()

        self.enable_tab_closing()
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
        if isinstance(widget, (tk.Entry, CTkEntry, tk.Text)):
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
            if isinstance(target, (CTkEntry, tk.Entry)):
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
    def _bind_recursive(self, widget, handler_fn):
        for child in widget.winfo_children():
            if isinstance(child, (tk.Entry, CTkEntry)):
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
    def start_tutorial(self, manual=False):
        self.tutorial_pending = False
        if self.tutorial_active:
            return
        if self.tutorial_cancelled_this_session and not manual:
            return

        if manual:
            self.tutorial_cancelled_this_session = False

        steps = [
            ("Welcome to CleanCutPDF!",
             "This tutorial will guide you through the core features of the app.",
             "Split & Rename"),
            ("Split & Rename Tab",
             "This is where you drag and drop PDFs or click Open PDF. Split markers like 'SPLIT HERE' are detected automatically.",
             "Split & Rename"),
            ("Editing Parts",
             "Each split part has Revoked, Agency, Description, and Date fields. The left side scrolls when a file contains many parts.",
             "Split & Rename"),
            ("Client Name",
             "Enter the client name for the current file. You can choose whether a client folder is created before exporting.",
             "Split & Rename"),
            ("Keyboard Shortcuts",
             "Click 'Show Keybinds' while working, or customize shortcuts in the Keybinds tab.",
             "Split & Rename"),
            ("Exporting",
             "Click 'Export PDFs' to create the files. Blank dates give you a warning but can still be exported.",
             "Split & Rename"),
            ("Quick Split Tab",
             "Use Quick Split for fast splitting when no metadata or custom naming is needed.",
             "Quick Split"),
            ("Settings Tab",
             "Settings are organized into sections on the left.",
             "Settings"),
            ("Appearance Settings",
             "Change theme, font size, and font family here.",
             "Settings", lambda: self._show_settings_section("Appearance")),
            ("Export Settings",
             "Choose the export folder, logging, and filename/title template here.",
             "Settings", lambda: self._show_settings_section("Export")),
            ("Behavior Settings",
             "Control blank-page removal, description autofill, date warnings, session restore, and updates here.",
             "Settings", lambda: self._show_settings_section("Behavior")),
            ("License Settings",
             "View or clear license information here.",
             "Settings", lambda: self._show_settings_section("License")),
            ("Logs Tab",
             "Search, sort, filter, and export past activity from the Logs tab.",
             "Logs"),
            ("Keybinds Tab",
             "Click a shortcut to capture a new key combination. Changes are saved immediately.",
             "Keybinds"),
            ("You're Ready!",
             "That's it. You can run this tutorial again from Settings at any time.",
             "Split & Rename")
        ]

        self.tutorial_active = True
        state = {"index": 0, "window": None}

        def cancel_tutorial():
            window = state.get("window")
            if window and window.winfo_exists():
                try:
                    window.grab_release()
                except tk.TclError:
                    pass
                window.destroy()
            self.tutorial_active = False
            self.tutorial_pending = False
            self.tutorial_cancelled_this_session = True
            debug("Tutorial cancelled by user", "debug")

        def complete_tutorial():
            window = state.get("window")
            if window and window.winfo_exists():
                try:
                    window.grab_release()
                except tk.TclError:
                    pass
                window.destroy()
            self.settings["tutorial_shown"] = True
            self.save_settings()
            self.tutorial_active = False
            self.tutorial_pending = False
            self.tutorial_cancelled_this_session = False
            debug("Tutorial completed", "debug")

        def show_step(index):
            if index >= len(steps):
                complete_tutorial()
                return

            state["index"] = index
            title, msg, tab = steps[index][:3]
            callback = steps[index][3] if len(steps[index]) > 3 else None

            try:
                self.notebook.set(tab)
                if callback:
                    callback()
            except Exception as error:
                debug(f"Tutorial navigation warning: {error}", "warning")

            window = state.get("window")
            if window and window.winfo_exists():
                window.destroy()

            window = tk.Toplevel(self)
            if self.theme == "Light Pink":
                tutorial_bg = "#fdf0f5"
                tutorial_text = "#1e1e1e"
                tutorial_muted = "#666666"

            elif self.theme == "Light Blue":
                tutorial_bg = "#f5f5f5"
                tutorial_text = "#1e1e1e"
                tutorial_muted = "#666666"

            else:
                tutorial_bg = "#292929"
                tutorial_text = "#ffffff"
                tutorial_muted = "#aaaaaa"

            window.configure(bg=tutorial_bg)
            state["window"] = window
            window.title(f"CleanCutPDF Tutorial — {index + 1}/{len(steps)}")
            window.geometry("560x285")
            window.resizable(False, False)
            window.transient(self)
            window.protocol("WM_DELETE_WINDOW", cancel_tutorial)

            self.update_idletasks()
            x = self.winfo_rootx() + max(0, (self.winfo_width() - 560) // 2)
            y = self.winfo_rooty() + max(0, (self.winfo_height() - 285) // 2)
            window.geometry(f"560x285+{x}+{y}")

            mode = ctk.get_appearance_mode()

            if mode == "Light":
                text_color = "#222222"
            else:
                text_color = "#ffffff"

            tk.Label(
                window,
                text=title,
                font=(self.font_family, self.font_size + 4, "bold"),
                fg=tutorial_text,
                bg=tutorial_bg
            ).pack(pady=(24, 10), padx=24)

            tk.Label(
                window,
                text=msg,
                font=(self.font_family, self.font_size),
                fg=tutorial_text,
                bg=tutorial_bg,
                wraplength=500,
                justify="center"
            ).pack(fill="x", padx=28, pady=(0, 18))

            tk.Label(
                window,
                text=f"Step {index + 1} of {len(steps)}",
                font=(self.font_family, max(10, self.font_size - 1)),
                fg=tutorial_muted,
                bg=tutorial_bg
            ).pack()

            button_row = ctk.CTkFrame(window, fg_color="transparent")
            button_row.pack(pady=(16, 18))

            ctk.CTkButton(
                button_row,
                text="Exit Tutorial",
                width=120,
                command=cancel_tutorial,
                text_color = text_color
            ).pack(side="left", padx=8)

            next_text = "Finish" if index == len(steps) - 1 else "Next"
            next_command = complete_tutorial if index == len(steps) - 1 else lambda: show_step(index + 1)
            ctk.CTkButton(
                button_row,
                text=next_text,
                width=120,
                text_color=text_color,
                command=next_command
            ).pack(side="left", padx=8)

            window.after(50, window.grab_set)
            window.after(80, window.focus_force)

        show_step(0)

    def reset_tutorial(self):
        self.settings["tutorial_shown"] = False
        self.save_settings()
        messagebox.showinfo("Tutorial Reset", "The tutorial will run again next time you launch the app.")

    # ─── Licenses ───
    def check_license(self):
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
            self.hide_loading_overlay()
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