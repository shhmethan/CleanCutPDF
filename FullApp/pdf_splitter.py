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
import secrets
import faulthandler
import threading
import traceback
from decimal import Decimal, InvalidOperation

# ─── Third-Party Libraries ───────────────────────────────────────────
import pymupdf as fitz
from PIL import Image, ImageTk, ImageStat
from PyPDF2 import PdfReader, PdfWriter

# ─── GUI: Tkinter & CustomTkinter ────────────────────────────────────
import tkinter as tk
from tkinter import ttk
import tkinter.scrolledtext as st
from tkinter import filedialog, messagebox, simpledialog, colorchooser
from tkinterdnd2 import DND_FILES, TkinterDnD
import customtkinter as ctk
from customtkinter import CTkImage

# ───── CONSTANTS & CONFIG ─────
CURRENT_VERSION = "1.10.2"
MAX_RENDERED_PDF_TABS = 3
VERSION_URL = "https://raw.githubusercontent.com/shhmethan/CleanCutPDF/refs/heads/master1/version.json"

# CleanCutPDF 2.x has its own release manifest. Once that manifest sets
# "legacy_upgrade": true, this app offers the upgrade: it downloads the 2.x
# installer, checks its SHA-256, runs it, and closes. The installer replaces
# this program in place; nothing in ~/.cleancutpdf is changed, and 2.x imports
# it on first start.
# CLEANCUTPDF_UPGRADE_MANIFEST points at another manifest for rehearsing the
# upgrade before release (https, or http on this computer only).
UPGRADE_URL = (
    os.environ.get("CLEANCUTPDF_UPGRADE_MANIFEST")
    or "https://raw.githubusercontent.com/shhmethan/CleanCutPDF/refs/heads/master1/CleanCutPDF.Avalonia/version.json"
)

BASE_DIR = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).parent
USER_DATA_DIR = Path.home() / ".cleancutpdf"
APP_ICON = BASE_DIR / "resources" / "favicon.ico"

USER_DATA_DIR.mkdir(exist_ok=True)
SETTINGS_FILE = USER_DATA_DIR / "settings.json"
LOG_FILE = USER_DATA_DIR / "full.log"
DEBUG_FILE = USER_DATA_DIR / "debug.log"
CRASH_FILE = USER_DATA_DIR / "crash.log"
LAST_ACTION_FILE = USER_DATA_DIR / "last_action.json"
KEYBINDS_FILE = USER_DATA_DIR / "keybinds.json"
PINK_LIGHT = USER_DATA_DIR / "pink_light.json"
PINK_DARK = USER_DATA_DIR / "pink_dark.json"
SESSION_FILE = USER_DATA_DIR / "sessions.json"
PROJECT_FILE = USER_DATA_DIR / "document_project.json"
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
DEFAULT_CUSTOM_FIELDS = {
    "revoked": {
        "key": "revoked", "label": "Revoked", "type": "toggle", "placement": "header",
        "default": False, "required": False, "autofill": True, "system": True
    },
    "agency": {
        "key": "agency", "label": "Agency Code", "type": "text", "placeholder": "F",
        "default": "", "required": False, "autofill": True, "system": True,
        "tooltip": "Agency Codes:\n• I = IRS\n• F = FTB\n• E = EDD\n• C = CDTFA\n• B = BOE"
    },
    "description": {
        "key": "description", "label": "Description", "type": "text", "placeholder": "POA",
        "default": "POA", "required": False, "autofill": True, "title_case": True, "system": True
    },
    "date": {
        "key": "date", "label": "Date", "type": "date", "placeholder": "e.g. 8-20-2026",
        "default": "", "required": False, "autofill": True, "auto_today": False,
        "date_format": "M-D-YYYY", "system": True
    },
    "matter_number": {
        "key": "matter_number", "label": "Matter / Case #", "type": "text",
        "placeholder": "Matter or case number", "default": "", "required": False,
        "autofill": True, "system": True
    },
    "document_type": {
        "key": "document_type", "label": "Document Type", "type": "text",
        "placeholder": "e.g. Notice, Letter, Filing", "default": "", "required": False,
        "autofill": True, "title_case": True, "system": True
    },
    # Pre-loaded accounting fields requested for the reusable field library.
    # They are available to every workspace but are not assigned automatically,
    # so existing workspace layouts remain unchanged after an update.
    "amount": {
        "key": "amount", "label": "Amount", "type": "currency",
        "placeholder": "e.g. 134.06", "default": "", "required": False,
        "autofill": False, "title_case": False, "system": True
    },
    "payment_method": {
        "key": "payment_method", "label": "Payment Method", "type": "choice",
        "placeholder": "", "default": "", "required": False,
        "autofill": False, "title_case": False,
        "options": ["ACH", "CC", "CK", "Other"], "system": True
    },
    "check_number": {
        "key": "check_number", "label": "Check Number", "type": "text",
        "placeholder": "e.g. 1234", "default": "", "required": False,
        "autofill": False, "title_case": False,
        "condition": {"field": "payment_method", "equals": "CK"}, "system": True
    },
    "company": {
        "key": "company", "label": "Company", "type": "choice",
        "placeholder": "", "default": "", "required": False,
        "autofill": False, "title_case": False,
        "options": ["JARB", "AB INC", "JL APC", "JARB LLC", "Other"], "system": True
    }
}

DEFAULT_WORKSPACE_DEFINITIONS = {
    "Accounting": {
        "client_label": "Client Name",
        "summary": "Accounting and tax-document workflow with agency, revoked status, description, and date.",
        "filename_template": "{client}_{revoked}_{agency_description}_{date}",
        "field_keys": ["revoked", "agency", "description", "date"],
        "field_overrides": {
            "description": {"default": "POA", "autofill": True}
        },
        "notes": [],
        "custom_layout": None,
        "permanent": True
    },
    "Legal": {
        "client_label": "Client / Matter Name",
        "summary": "Legal workflow with matter/case number, document type, description, and document date.",
        "filename_template": "{client}_{matter_number}_{document_type}_{description}_{date}",
        "field_keys": ["matter_number", "document_type", "description", "date"],
        "field_overrides": {
            "description": {"default": "", "autofill": True}
        },
        "notes": [],
        "custom_layout": None,
        "permanent": False
    }
}

CUSTOM_FIELD_TYPE_LABELS = {
    "text": "Text",
    "number": "Number",
    "currency": "Currency",
    "date": "Date",
    "choice": "Dropdown / Choice",
    "checkbox": "Checkbox",
    "toggle": "Toggle"
}
DATE_FORMATS = ["M-D-YYYY", "MM-DD-YYYY", "YYYY.MM.DD", "MMDDYY"]
QUICK_SPLIT_FILENAME_ORDERS = [
    "Original Name - Part Number",
    "Part Number - Original Name",
    "Original Name Only",
    "Part Number Only"
]

# Runtime-materialized workspace profiles.  These are rebuilt from settings so
# the rest of the app can continue using the existing WORKSPACES interface.
WORKSPACES = {}


DEFAULT_SETTINGS = {
    "font_family": "Segoe UI",
    "font_size": 12,
    "theme": "Light Blue",
    "export_folder": "",
    "retain_client_name": False,
    "remove_blank_pages": True,
    "folder_shortcuts": [],
    "quick_split_filename_order": "Original Name - Part Number",
    "export_log_enabled": True,
    "auto_restore_session": True,
    "tutorial_shown": False,
    "suppressFutureDateWarning": False,
    "suppressNoSplitWarning": False,
    "check_updates_on_startup": True,
    "autofill_description": True,
    "default_description": "POA",
    "filename_template": "{client}_{revoked}_{agency_description}_{date}",
    "default_workspace": "Accounting",
    "custom_fields": copy.deepcopy(DEFAULT_CUSTOM_FIELDS),
    "workspaces": copy.deepcopy(DEFAULT_WORKSPACE_DEFINITIONS),
    # Retained only for migration/backward compatibility with v1.8 and older.
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
MAX_DEBUG_ENTRIES = 2500
MAX_LOG_ENTRIES = 2500
MAX_LOG_BYTES = 4 * 1024 * 1024
DEBUG_FILE_WRITE_TYPES = {"warning", "error", "saved", "skip", "keybind", "log", "update", "undo"}


def _atomic_json_dump(path, value):
    """Write JSON through a temporary file so interrupted saves do not corrupt it."""
    path = Path(path)
    temporary = path.with_name(f".{path.name}.tmp")
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


_fault_log_handle = None
try:
    # faulthandler records native crashes (for example, a Tk/PDF rendering
    # failure) that never reach Python's normal exception hook.
    _fault_log_handle = open(CRASH_FILE, "a", encoding="utf-8", buffering=1)
    faulthandler.enable(file=_fault_log_handle, all_threads=True)
except Exception:
    _fault_log_handle = None


_last_action_state = {
    "time": None,
    "action": "Application starting",
    "details": ""
}


def _record_last_action(action, details=""):
    """Persist the last UI phase so forced exits still leave diagnostics."""
    global _last_action_state
    _last_action_state = {
        "time": datetime.datetime.now().isoformat(timespec="seconds"),
        "action": str(action),
        "details": str(details or "")
    }
    try:
        _atomic_json_dump(LAST_ACTION_FILE, _last_action_state)
    except Exception:
        pass


def _write_handled_exception(context, error):
    """Append a handled callback failure with the current action context."""
    try:
        with open(CRASH_FILE, "a", encoding="utf-8") as handle:
            handle.write(f"\n[{datetime.datetime.now().isoformat()}] HANDLED ERROR: {context}\n")
            handle.write(f"Last action: {_last_action_state!r}\n")
            traceback.print_exception(type(error), error, error.__traceback__, file=handle)
    except Exception:
        pass


def _write_uncaught_exception(exc_type, exc_value, exc_traceback):
    """Record uncaught exceptions so a failed launch can be diagnosed."""
    try:
        import traceback
        with open(CRASH_FILE, "a", encoding="utf-8") as handle:
            handle.write(f"\n[{datetime.datetime.now().isoformat()}]\n")
            handle.write(f"Last action: {_last_action_state!r}\n")
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=handle)
    except Exception:
        pass


sys.excepthook = _write_uncaught_exception


def _write_thread_exception(args):
    _write_uncaught_exception(args.exc_type, args.exc_value, args.exc_traceback)


if hasattr(threading, "excepthook"):
    threading.excepthook = _write_thread_exception

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
    if len(debug_log) > MAX_DEBUG_ENTRIES:
        del debug_log[:-MAX_DEBUG_ENTRIES]
    print(full_message)

    # Page scanning can produce thousands of debug messages. Keep those in the
    # bounded in-memory console, but avoid synchronous disk I/O for each page.
    if type not in DEBUG_FILE_WRITE_TYPES:
        return
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

def _is_trusted_upgrade_link(url):
    """https anywhere, or plain http only for this computer (upgrade rehearsals)."""
    lowered = url.lower()
    if lowered.startswith("https://"):
        return True
    return lowered.startswith(("http://127.0.0.1:", "http://127.0.0.1/", "http://localhost:", "http://localhost/"))


def read_upgrade_offer(data):
    """Return the CleanCutPDF 2 upgrade described by the 2.x manifest, or None.

    The offer is made only when the manifest explicitly allows it
    ("legacy_upgrade": true) and carries an installer link plus its SHA-256,
    so a preview build of 2.x is never pushed to 1.x users by accident.
    """
    if not isinstance(data, dict) or data.get("legacy_upgrade") is not True:
        return None

    version = str(data.get("version", "")).strip()
    url = str(data.get("download_url", "")).strip()
    sha256 = str(data.get("sha256", "")).strip().lower()

    if not version or parse_version(version) <= parse_version(CURRENT_VERSION):
        return None
    if not _is_trusted_upgrade_link(url) or not url.lower().split("?")[0].endswith(".exe"):
        return None
    if len(sha256) != 64 or any(char not in "0123456789abcdef" for char in sha256):
        return None

    changelog = data.get("changelog", {})
    notes = changelog.get(version, []) if isinstance(changelog, dict) else []
    return {
        "version": version,
        "download_url": url,
        "sha256": sha256,
        "notes": [str(line) for line in notes] if isinstance(notes, list) else []
    }


def download_verified(url, sha256, target, progress=None):
    """Download url to target and verify its SHA-256.

    A file that does not match is deleted and never run. progress, when
    given, is called with (bytes_received, total_bytes_or_None).
    """
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    digest = hashlib.sha256()

    try:
        request = urllib.request.Request(url, headers={"User-Agent": "CleanCutPDF"})
        with urllib.request.urlopen(request, timeout=30) as response:
            total = response.headers.get("Content-Length")
            total = int(total) if total and total.isdigit() else None
            received = 0
            with open(partial, "wb") as output:
                while True:
                    chunk = response.read(1024 * 256)
                    if not chunk:
                        break
                    output.write(chunk)
                    digest.update(chunk)
                    received += len(chunk)
                    if progress:
                        progress(received, total)

        if digest.hexdigest().lower() != sha256.lower():
            raise ValueError("The downloaded installer failed SHA-256 verification, so it was not run.")

        if target.exists():
            target.unlink()
        partial.rename(target)
        return target
    finally:
        if partial.exists():
            try:
                partial.unlink()
            except OSError:
                pass


def upgrade_install_command(installer, install_dir):
    """Command line that installs CleanCutPDF 2 over this copy and starts it.

    One string, not a list: NSIS needs /D= last and unquoted even when the
    folder has spaces, and a list would make Python add quotes.
    """
    return f'"{installer}" /S /RELAUNCH /D={str(install_dir).rstrip(chr(92))}'


class CTkUndoEntry(ctk.CTkEntry):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._undo_stack = []
        self._redo_stack = []
        self._last_value = self.get()
        self._typing_timer = None

        self.after(10, self._bind_events)

    def _bind_events(self):
        if not self._widget_exists():
            return
        try:
            self._entry.bind("<Key>", self._on_keypress)
            self._entry.bind("<Control-z>", self._undo)
            self._entry.bind("<Control-y>", self._redo)
            debug("[UNDO] Smart undo/redo system initialized", "undo")
        except Exception as e:
            debug(f"[UNDO] Failed to bind events: {e}", "error")

    def _on_keypress(self, event=None):
        if not self._widget_exists():
            return
        keys_to_commit_immediately = ["Return", "Tab", "space"]

        if event.keysym in keys_to_commit_immediately:
            self._commit_snapshot()
            return

        if self._typing_timer:
            self.after_cancel(self._typing_timer)

        # Wait 600ms before committing this snapshot
        self._typing_timer = self.after(600, self._commit_snapshot)

    def _commit_snapshot(self):
        if not self._widget_exists():
            self._typing_timer = None
            return
        current = self.get()
        if current != self._last_value:
            self._undo_stack.append(self._last_value)
            self._redo_stack.clear()
            debug(f"[UNDO] Committed snapshot: '{self._last_value}'", "undo")
            self._last_value = current

    def _undo(self, event=None):
        if not self._widget_exists():
            return "break"
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
        if not self._widget_exists():
            return "break"
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

    def _widget_exists(self):
        try:
            return bool(self.winfo_exists() and self._entry.winfo_exists())
        except tk.TclError:
            return False

    def destroy(self):
        if self._typing_timer:
            try:
                self.after_cancel(self._typing_timer)
            except tk.TclError:
                pass
            self._typing_timer = None
        try:
            self._entry.unbind("<Key>")
            self._entry.unbind("<Control-z>")
            self._entry.unbind("<Control-y>")
        except tk.TclError:
            pass
        super().destroy()

CTkEntry = CTkUndoEntry

class PDFSplitterApp(TkinterDnD.Tk):
    # ─── INITIALIZATION ───
    def _set_main_window_title(self):
        """Keep the app version visible in the main window title."""
        company = getattr(self, "licensed_company", "Unlicensed") or "Unlicensed"
        if company != "Unlicensed":
            self.title(f"CleanCutPDF v{CURRENT_VERSION} – Licensed to {company}")
        else:
            self.title(f"CleanCutPDF v{CURRENT_VERSION}")

    def report_callback_exception(self, exc, val, tb):
        """Log Tk callback failures instead of letting the GUI disappear."""
        try:
            with open(CRASH_FILE, "a", encoding="utf-8") as handle:
                handle.write(f"\n[{datetime.datetime.now().isoformat()}] TK CALLBACK ERROR\n")
                handle.write(f"Last action: {_last_action_state!r}\n")
                traceback.print_exception(exc, val, tb, file=handle)
        except Exception:
            pass

        debug(f"Tk callback error during {_last_action_state.get('action', 'unknown action')}: {val}", "error")
        try:
            messagebox.showerror(
                "CleanCutPDF Error",
                "CleanCutPDF caught an interface error and kept the window open.\n\n"
                f"The details were saved to:\n{CRASH_FILE}"
            )
        except Exception:
            pass

    def __init__(self):
        super().__init__()
        self.start_time = time.perf_counter()

        if APP_ICON.exists():
            try:
                self.iconbitmap(str(APP_ICON))
            except Exception as e:
                debug(f"Could not load app icon: {e}", "warning")

        self.pdf_sessions = {}
        self.active_pdf_session = None
        self.settings = {}

        # Load license info
        if LICENSE_FILE.exists():
            with open(LICENSE_FILE, "r") as f:
                license_data = json.load(f)
            self.licensed_company = license_data.get("company", "Unknown")
            self._set_main_window_title()
        else:
            self.licensed_company = "Unlicensed"
            self._set_main_window_title()
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
        self.rename_only_tab = self.notebook.add("Rename Only")
        self.settings_tab = self.notebook.add("Settings")
        self.log_tab = self.notebook.add("Logs")
        self.about_tab = self.notebook.add("About")
        self.keybinds_tab = self.notebook.add("Keybinds")
        self.help_tab = self.notebook.add("Help")

        self.build_splitter_tab()
        self.build_quick_split_tab(self.quick_splitter_tab)
        self.build_rename_only_tab()
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

                # 1.x is current: see whether CleanCutPDF 2 is offered.
                self.check_for_upgrade(manual=False)


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

                # 1.x is current: see whether CleanCutPDF 2 is offered.
                if self.check_for_upgrade(manual=True):
                    return

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
    def check_for_upgrade(self, manual=False):
        """Offer CleanCutPDF 2 when its manifest allows it. Returns True if it was offered."""
        try:
            with urllib.request.urlopen(UPGRADE_URL, timeout=10) as response:
                offer = read_upgrade_offer(json.loads(response.read().decode("utf-8")))
        except Exception as error:
            # Like the update check, this must never interrupt normal use.
            debug(f"CleanCutPDF 2 upgrade check failed: {error}", "error")
            return False

        if offer is None:
            debug("CleanCutPDF 2 upgrade is not offered yet.", "update")
            return False

        version = offer["version"]

        # At startup, ask once per version; Check for Updates always asks.
        if not manual and self.settings.get("skipped_upgrade_version") == version:
            debug(f"CleanCutPDF {version} upgrade was postponed earlier.", "update")
            return False

        notes = "\n".join(f"• {line}" for line in offer["notes"][:8])
        confirm = messagebox.askyesno(
            "CleanCutPDF 2 Is Available",

            f"CleanCutPDF {version} is the new version of CleanCutPDF.\n\n"

            + (f"What's new:\n{notes}\n\n" if notes else "")

            + "Upgrading replaces this program. Your settings, workspaces, custom fields, "
              "open PDFs, and export history are kept, and CleanCutPDF 2 offers to bring "
              "them in the first time it starts.\n\n"

              "Would you like to upgrade now?"
        )

        if not confirm:
            debug(f"User postponed the CleanCutPDF {version} upgrade.", "update")
            if not manual:
                self.save_setting("skipped_upgrade_version", version)
            return True

        debug(f"User accepted the CleanCutPDF {version} upgrade.", "update")
        self.start_upgrade(offer)
        return True

    def start_upgrade(self, offer):
        """Download the CleanCutPDF 2 installer, verify it, run it, and close."""
        if not getattr(sys, "frozen", False):
            # Running from source (PyCharm): there is no installed program to replace.
            messagebox.showinfo(
                "CleanCutPDF 2",
                "This copy is running from source, so it cannot be upgraded in place.\n\n"
                f"Installer: {offer['download_url']}"
            )
            return

        version = offer["version"]
        install_dir = Path(sys.executable).parent
        installer = Path(tempfile.gettempdir()) / "CleanCutPDFUpdate" / f"CleanCutPDF-{version}-Setup.exe"

        popup = ctk.CTkToplevel(self)
        popup.title("Upgrading CleanCutPDF")
        popup.geometry("440x150")
        popup.resizable(False, False)
        popup.transient(self)
        popup.protocol("WM_DELETE_WINDOW", lambda: None)  # The download is short; closing mid-way is not offered.

        status = ctk.CTkLabel(
            popup,
            text=f"Downloading CleanCutPDF {version}...",
            font=(self.font_family, self.font_size)
        )
        status.pack(pady=(24, 10))
        bar = ctk.CTkProgressBar(popup, width=360)
        bar.set(0)
        bar.pack(pady=(0, 10))

        def report(received, total):
            if total:
                fraction = min(1.0, received / total)
                self.after(0, lambda: (
                    bar.set(fraction),
                    status.configure(text=f"Downloading CleanCutPDF {version}... {int(fraction * 100)}%")
                ))

        def finish():
            try:
                status.configure(text="Installing... CleanCutPDF will close and reopen.")
                bar.set(1)
                self.save_sessions()
                subprocess.Popen(upgrade_install_command(installer, install_dir))
                debug(f"CleanCutPDF {version} installer started.", "update")
                # Close so the installer can replace this program.
                self.after(300, self._on_close)
            except Exception as error:
                fail(error)

        def fail(error):
            debug(f"CleanCutPDF {version} upgrade failed: {error}", "error")
            try:
                popup.destroy()
            except tk.TclError:
                pass
            messagebox.showerror(
                "Upgrade Failed",
                f"CleanCutPDF {version} could not be installed.\n\n{error}\n\n"
                "Nothing was changed. You can keep working and try again later."
            )

        def worker():
            try:
                download_verified(offer["download_url"], offer["sha256"], installer, report)
                self.after(0, finish)
            except Exception as error:
                self.after(0, lambda: fail(error))

        threading.Thread(target=worker, daemon=True).start()

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
        canvas.create_text(
            overlay_w // 2, 33,
            text=message,
            fill=active_color,
            font=(self.font_family, max(10, self.font_size - 1), "bold"),
            width=overlay_w - 24
        )
        y_pos = 82

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
        self.settings = copy.deepcopy(DEFAULT_SETTINGS)
        user_settings = {}

        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                user_settings = json.load(f)
            if not isinstance(user_settings, dict):
                raise ValueError("Invalid settings format")
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            debug("Creating or repairing settings.json with default values", "warning")
            user_settings = {}

        # Ordinary top-level settings.
        nested_keys = {"custom_fields", "workspaces", "workspace_settings"}
        for key, value in user_settings.items():
            if key not in nested_keys:
                self.settings[key] = value

        shortcuts = self.settings.get("folder_shortcuts", [])
        if not isinstance(shortcuts, list):
            shortcuts = []
        normalized_shortcuts = []
        for shortcut in shortcuts:
            if not isinstance(shortcut, dict) or not shortcut.get("path"):
                continue
            normalized = copy.deepcopy(shortcut)
            normalized.setdefault("label", Path(str(shortcut["path"])).name or "Folder")
            normalized.setdefault("icon", "📁")
            normalized.setdefault("color", "")
            normalized_shortcuts.append(normalized)
        self.settings["folder_shortcuts"] = normalized_shortcuts

        # Reusable field library. Built-in fields are always restored if an old
        # settings file does not contain them, while user-created fields are retained.
        fields = copy.deepcopy(DEFAULT_CUSTOM_FIELDS)
        saved_fields = user_settings.get("custom_fields", {})
        if isinstance(saved_fields, dict):
            for key, config in saved_fields.items():
                if not isinstance(config, dict):
                    continue
                existing = fields.get(key, {})
                existing.update(copy.deepcopy(config))
                existing["key"] = key
                fields[key] = existing
        for field in fields.values():
            if isinstance(field, dict):
                field.setdefault("color", "")
                field.setdefault("auto_today", False)

        # v1.9.18 offered a global date-autofill setting.  Preserve its effect
        # on upgrade, but make it an explicit property of each Date field now.
        if user_settings.get("autofill_todays_date", False):
            for field in fields.values():
                if isinstance(field, dict) and field.get("type") == "date":
                    field["auto_today"] = True
        self.settings.pop("autofill_todays_date", None)

        self.settings["custom_fields"] = fields

        # Workspace definitions. Accounting is permanent; every other workspace
        # can be created, renamed, or deleted by the user.
        workspaces = copy.deepcopy(DEFAULT_WORKSPACE_DEFINITIONS)
        saved_workspaces = user_settings.get("workspaces", {})
        if isinstance(saved_workspaces, dict) and saved_workspaces:
            workspaces = {}
            for name, definition in saved_workspaces.items():
                if isinstance(definition, dict):
                    workspaces[name] = copy.deepcopy(definition)

            # Accounting can never disappear, even if an older/broken settings
            # file omitted it.
            if "Accounting" not in workspaces:
                workspaces["Accounting"] = copy.deepcopy(DEFAULT_WORKSPACE_DEFINITIONS["Accounting"])

        accounting = workspaces.setdefault(
            "Accounting",
            copy.deepcopy(DEFAULT_WORKSPACE_DEFINITIONS["Accounting"])
        )
        accounting["permanent"] = True

        # v1.8 migration: its workspace_settings object stored filename/default
        # Description behavior separately from the workspace profile.
        saved_workspace_settings = user_settings.get("workspace_settings", {})
        if not isinstance(saved_workspace_settings, dict):
            saved_workspace_settings = {}

        for workspace_name, old_settings in saved_workspace_settings.items():
            if workspace_name not in workspaces or not isinstance(old_settings, dict):
                continue
            definition = workspaces[workspace_name]
            if old_settings.get("filename_template"):
                definition["filename_template"] = old_settings["filename_template"]
            overrides = definition.setdefault("field_overrides", {})
            desc_override = overrides.setdefault("description", {})
            if "default_description" in old_settings:
                desc_override["default"] = old_settings["default_description"]
            if "autofill_description" in old_settings:
                desc_override["autofill"] = bool(old_settings["autofill_description"])

        # Pre-workspace migration.
        if "workspace_settings" not in user_settings and "Accounting" in workspaces:
            definition = workspaces["Accounting"]
            definition["filename_template"] = user_settings.get(
                "filename_template",
                definition.get("filename_template", "{client}_{revoked}_{agency_description}_{date}")
            )
            desc_override = definition.setdefault("field_overrides", {}).setdefault("description", {})
            desc_override["default"] = user_settings.get("default_description", "POA")
            desc_override["autofill"] = user_settings.get("autofill_description", True)

        # Normalize every workspace and discard references to deleted fields.
        for name, definition in workspaces.items():
            definition.setdefault("client_label", "Client Name")
            definition.setdefault("summary", "Custom document workflow.")
            definition.setdefault("filename_template", "{client}_{date}")
            definition.setdefault("field_overrides", {})
            definition.setdefault("permanent", name == "Accounting")
            field_keys = definition.get("field_keys", [])
            if not isinstance(field_keys, list):
                field_keys = []
            definition["field_keys"] = [key for key in field_keys if key in fields]

            raw_notes = definition.get("notes", [])
            if not isinstance(raw_notes, list):
                raw_notes = []
            valid_note_positions = set(definition["field_keys"]) | {"__top__", "__end__"}
            normalized_notes = []
            for note in raw_notes:
                if not isinstance(note, dict):
                    continue
                text = str(note.get("text", "")).strip()
                if not text:
                    continue
                before_field = note.get("before_field", "__end__")
                if before_field not in valid_note_positions:
                    before_field = "__end__"
                normalized_notes.append({
                    "id": str(note.get("id") or secrets.token_hex(4)),
                    "text": text,
                    "before_field": before_field
                })
            definition["notes"] = normalized_notes

            # Optional visual layout. None means the normal automatic layout is used.
            # v2 stores true freeform rectangles (x/y/width/height). Older 3-column
            # layouts are migrated forward so existing test layouts keep working.
            layout = definition.get("custom_layout")
            if not isinstance(layout, dict) or not layout.get("enabled"):
                definition["custom_layout"] = None
            else:
                surface = layout.get("surface", {}) if isinstance(layout.get("surface"), dict) else {}
                try:
                    surface_w = max(640, int(surface.get("width", 920)))
                    surface_h = max(420, int(surface.get("height", 620)))
                except Exception:
                    surface_w, surface_h = 920, 620

                clean_elements = {}
                raw_elements = layout.get("elements", {})
                if isinstance(raw_elements, dict):
                    for key, box in raw_elements.items():
                        # A layout tile is valid only while the field is still
                        # assigned to this workspace. Keeping an old tile here
                        # made an unassigned field appear to come back later.
                        if key not in definition["field_keys"]:
                            continue
                        if not isinstance(box, dict):
                            continue
                        try:
                            x = max(0, int(box.get("x", 0)))
                            y = max(0, int(box.get("y", 0)))
                            width = max(90, int(box.get("width", 240)))
                            height = max(84, int(box.get("height", 84)))
                        except Exception:
                            continue
                        clean_elements[key] = {"x": x, "y": y, "width": width, "height": height}

                # Migrate the earlier row/column/span format to approximate
                # freeform rectangles. This is only used for layouts saved by the
                # first Workspace Designer build.
                if not clean_elements:
                    positions = layout.get("field_positions", {})
                    if not isinstance(positions, dict):
                        positions = {}
                    cell_w = 190
                    cell_h = 86
                    for index, key in enumerate(definition["field_keys"]):
                        if key not in fields:
                            continue
                        pos = positions.get(key, {}) if isinstance(positions.get(key), dict) else {}
                        try:
                            row = max(0, int(pos.get("row", index)))
                            col = max(0, min(2, int(pos.get("col", 0))))
                            span = max(1, min(3 - col, int(pos.get("span", 3))))
                        except Exception:
                            row, col, span = index, 0, 3
                        clean_elements[key] = {
                            "x": 30 + col * cell_w,
                            "y": 55 + row * cell_h,
                            "width": max(150, span * cell_w - 14),
                            "height": 68
                        }

                definition["custom_layout"] = {
                    "enabled": True,
                    "version": 3,
                    "snap_to_grid": bool(layout.get("snap_to_grid", True)),
                    "grid_size": max(8, min(64, int(layout.get("grid_size", 24) or 24))),
                    "surface": {"width": surface_w, "height": surface_h},
                    "elements": clean_elements
                }

        self.settings["workspaces"] = workspaces

        if self.settings.get("default_workspace") not in workspaces:
            self.settings["default_workspace"] = "Accounting"

        # Keep legacy keys synchronized for older updater/build logic.
        accounting_override = workspaces["Accounting"].get("field_overrides", {}).get("description", {})
        self.settings["default_description"] = accounting_override.get(
            "default", fields.get("description", {}).get("default", "POA")
        )
        self.settings["autofill_description"] = accounting_override.get(
            "autofill", fields.get("description", {}).get("autofill", True)
        )
        self.settings["filename_template"] = workspaces["Accounting"].get(
            "filename_template", "{client}_{revoked}_{agency_description}_{date}"
        )

        # Keep a compatibility workspace_settings object so upgrades from this
        # build remain friendly to older code, even though workspaces is now the
        # real source of truth.
        self.settings["workspace_settings"] = {}
        for name, definition in workspaces.items():
            desc_override = definition.get("field_overrides", {}).get("description", {})
            self.settings["workspace_settings"][name] = {
                "default_description": desc_override.get("default", ""),
                "autofill_description": desc_override.get("autofill", True),
                "filename_template": definition.get("filename_template", "{client}_{date}")
            }

        self.rebuild_runtime_workspaces()
        self.save_settings()

        try:
            with open(KEYBINDS_FILE, "r", encoding="utf-8") as f:
                file_keybinds = json.load(f)
                if not isinstance(file_keybinds, dict):
                    raise ValueError("Keybinds file must be a dictionary")
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            debug("Generating default keybinds", "warning")
            file_keybinds = {}

        self.keybindings = {**DEFAULT_KEYBINDS, **file_keybinds}
        if self.keybindings != file_keybinds:
            with open(KEYBINDS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.keybindings, f, indent=2)

    def rebuild_runtime_workspaces(self):
        global WORKSPACES
        runtime = {}
        field_library = self.settings.setdefault("custom_fields", {})
        definitions = self.settings.setdefault("workspaces", {})

        for workspace_name, definition in definitions.items():
            fields = []
            overrides = definition.get("field_overrides", {})
            for key in definition.get("field_keys", []):
                base = field_library.get(key)
                if not isinstance(base, dict):
                    continue
                field = copy.deepcopy(base)
                field.update(copy.deepcopy(overrides.get(key, {})))
                field["key"] = key
                fields.append(field)

            runtime[workspace_name] = {
                "client_label": definition.get("client_label", "Client Name"),
                "summary": definition.get("summary", "Custom document workflow."),
                "default_filename_template": definition.get("filename_template", "{client}_{date}"),
                "filename_template": definition.get("filename_template", "{client}_{date}"),
                "permanent": bool(definition.get("permanent", workspace_name == "Accounting")),
                "fields": fields,
                "notes": copy.deepcopy(definition.get("notes", [])),
                "custom_layout": copy.deepcopy(definition.get("custom_layout"))
            }

        if "Accounting" not in runtime:
            # Should never happen because load_settings repairs it, but this keeps
            # the renderer safe if settings are edited while the app is open.
            definition = copy.deepcopy(DEFAULT_WORKSPACE_DEFINITIONS["Accounting"])
            fields = []
            for key in definition["field_keys"]:
                fields.append(copy.deepcopy(DEFAULT_CUSTOM_FIELDS[key]))
            runtime["Accounting"] = {
                "client_label": definition["client_label"],
                "summary": definition["summary"],
                "default_filename_template": definition["filename_template"],
                "filename_template": definition["filename_template"],
                "permanent": True,
                "fields": fields,
                "notes": copy.deepcopy(definition.get("notes", [])),
                "custom_layout": copy.deepcopy(definition.get("custom_layout"))
            }

        WORKSPACES.clear()
        WORKSPACES.update(runtime)

    def save_settings(self):
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _atomic_json_dump(SETTINGS_FILE, self.settings)

    def _default_pdf_project(self):
        return {
            "folders": [{"id": "inbox", "name": "Inbox", "parent_id": None}],
            "selected_folder_id": "inbox"
        }

    def load_pdf_project(self):
        project = self._default_pdf_project()
        try:
            if PROJECT_FILE.exists():
                with open(PROJECT_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                if isinstance(saved, dict):
                    folders = saved.get("folders")
                    if isinstance(folders, list):
                        valid = [
                            folder for folder in folders
                            if isinstance(folder, dict)
                            and folder.get("id")
                            and folder.get("name")
                        ]
                        if valid:
                            project["folders"] = valid
                    selected = saved.get("selected_folder_id")
                    if selected:
                        project["selected_folder_id"] = selected
        except (OSError, ValueError, TypeError) as error:
            debug(f"Could not load document project: {error}", "warning")

        folder_ids = {folder["id"] for folder in project["folders"]}
        if "inbox" not in folder_ids:
            project["folders"].insert(0, {"id": "inbox", "name": "Inbox", "parent_id": None})
        if project["selected_folder_id"] not in folder_ids:
            project["selected_folder_id"] = "inbox"
        self.pdf_project = project

    def save_pdf_project(self):
        try:
            _atomic_json_dump(PROJECT_FILE, self.pdf_project)
        except OSError as error:
            debug(f"Could not save document project: {error}", "error")

    def _pdf_folder_name(self, folder_id):
        for folder in getattr(self, "pdf_project", {}).get("folders", []):
            if folder.get("id") == folder_id:
                return folder.get("name", "Inbox")
        return "Inbox"

    def _pdf_file_signature(self, path):
        try:
            stat = Path(path).stat()
            return {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
        except OSError:
            return None

    def _selected_pdf_folder_id(self):
        selected = getattr(self, "pdf_project", {}).get("selected_folder_id", "inbox")
        folder_ids = {folder.get("id") for folder in self.pdf_project.get("folders", [])}
        return selected if selected in folder_ids else "inbox"

    def _selected_document_sessions(self):
        """Return the selected PDF sessions, or the active session as fallback."""
        sessions = []
        tree = getattr(self, "pdf_document_tree", None)
        if tree is not None:
            for item_id in tree.selection():
                if item_id.startswith("doc:"):
                    session = self.pdf_sessions.get(item_id[4:])
                    if session is not None:
                        sessions.append(session)
                elif item_id.startswith("folder:"):
                    folder_id = item_id[7:]
                    sessions.extend(
                        session for session in self.pdf_sessions.values()
                        if session.get("folder_id", "inbox") == folder_id
                    )
        if not sessions:
            active = self.get_active_session() if hasattr(self, "pdf_tabview") else None
            if active is not None:
                sessions = [active]
        unique = []
        seen = set()
        for session in sessions:
            key = id(session)
            if key not in seen:
                unique.append(session)
                seen.add(key)
        return unique

    def _refresh_pdf_sidebar(self):
        tree = getattr(self, "pdf_document_tree", None)
        if tree is None or getattr(self, "_refreshing_pdf_sidebar", False):
            return
        self._refreshing_pdf_sidebar = True
        try:
            selected_ids = set(tree.selection())
            for item_id in tree.get_children(""):
                tree.delete(item_id)

            folder_nodes = {}
            for folder in self.pdf_project.get("folders", []):
                folder_id = folder.get("id")
                if not folder_id:
                    continue
                folder_nodes[folder_id] = tree.insert(
                    "", "end", iid=f"folder:{folder_id}",
                    text=folder.get("name", "Folder")
                )
                if folder_id == "inbox":
                    tree.item(f"folder:{folder_id}", open=True)

            for pdf_name, session in self.pdf_sessions.items():
                folder_id = session.get("folder_id", "inbox")
                parent = folder_nodes.get(folder_id, folder_nodes.get("inbox", ""))
                workspace = session.get("workspace", "Accounting")
                display_text = f"{Path(session['path']).name}  [{workspace}]"
                tree.insert(
                    parent, "end", iid=f"doc:{pdf_name}",
                    text=display_text
                )

            # Treeview's #0 column otherwise stays at the sidebar width, which
            # makes a horizontal scrollbar exist without providing meaningful
            # extra content to scroll through. Size it to the longest visible
            # label so the full filename/workspace text is reachable.
            labels = []
            for item_id in tree.get_children(""):
                labels.append(str(tree.item(item_id, "text") or ""))
                labels.extend(
                    str(tree.item(child, "text") or "")
                    for child in tree.get_children(item_id)
                )
            max_label_chars = max((len(label) for label in labels), default=24)
            tree.column(
                "#0",
                width=max(260, max_label_chars * 8 + 36),
                minwidth=260,
                stretch=False
            )

            for item_id in selected_ids:
                if tree.exists(item_id):
                    tree.selection_add(item_id)

            if not tree.selection() and folder_nodes:
                selected_folder = f"folder:{self._selected_pdf_folder_id()}"
                if tree.exists(selected_folder):
                    tree.selection_set(selected_folder)
        finally:
            self._refreshing_pdf_sidebar = False

    def _update_pdf_sidebar_workspace_labels(self):
        """Update workspace labels without rebuilding the explorer tree."""
        tree = getattr(self, "pdf_document_tree", None)
        if tree is None:
            return
        for folder_node in tree.get_children(""):
            for document_node in tree.get_children(folder_node):
                if not document_node.startswith("doc:"):
                    continue
                session = self.pdf_sessions.get(document_node[4:])
                if session is None:
                    continue
                tree.item(
                    document_node,
                    text=f"{Path(session['path']).name}  [{session.get('workspace', 'Accounting')}]"
                )
        labels = []
        for item_id in tree.get_children(""):
            labels.append(str(tree.item(item_id, "text") or ""))
            labels.extend(
                str(tree.item(child, "text") or "")
                for child in tree.get_children(item_id)
            )
        max_label_chars = max((len(label) for label in labels), default=24)
        tree.column(
            "#0",
            width=max(260, max_label_chars * 8 + 36),
            minwidth=260,
            stretch=False
        )

    def _close_pdf_session(self, session, refresh=True):
        name = next((key for key, value in self.pdf_sessions.items() if value is session), None)
        if name is None:
            return
        tab_label = session.get("tab_label")
        try:
            was_visible = self.pdf_tabview.get() == tab_label
        except (tk.TclError, AttributeError):
            was_visible = False
        was_active = self.active_pdf_session is session or was_visible
        if was_active:
            try:
                if "➕ New PDF" in getattr(self.pdf_tabview, "_tabs", {}):
                    # Select the empty landing view before deleting the old
                    # tab; CTkTabview can otherwise leave the deleted frame
                    # painted until a later navigation event.
                    self.pdf_tabview.set("➕ New PDF")
            except tk.TclError:
                pass
            try:
                tab_frame = session.get("tab")
                if tab_frame is not None:
                    for child in tab_frame.winfo_children():
                        child.destroy()
            except (tk.TclError, AttributeError):
                pass
        try:
            if tab_label and tab_label in getattr(self.pdf_tabview, "_tabs", {}):
                self.pdf_tabview.delete(tab_label)
        except tk.TclError:
            pass
        self.pdf_sessions.pop(name, None)
        if self.active_pdf_session is session:
            self.active_pdf_session = None
        if was_active:
            # Deleting a CTkTabview tab can leave its old frame visible until
            # another tab is explicitly selected. Always clear the editor
            # after closing the active PDF so its preview cannot remain stale.
            try:
                if "➕ New PDF" in getattr(self.pdf_tabview, "_tabs", {}):
                    self.pdf_tabview.set("➕ New PDF")
                    self.active_pdf_session = None
            except tk.TclError:
                pass
        if refresh:
            self.save_sessions()
            self._refresh_pdf_navigation()
            self._refresh_pdf_sidebar()

    def close_selected_documents(self):
        sessions = self._selected_document_sessions()
        if not sessions:
            messagebox.showinfo("Close PDFs", "Select one or more PDFs first.")
            return
        names = [Path(session.get("path", "PDF")).name for session in sessions]
        if not messagebox.askyesno(
            "Close PDFs",
            f"Close {len(names)} selected PDF(s)?\n\n" + "\n".join(names[:8])
            + ("\n…" if len(names) > 8 else "")
        ):
            return
        for session in list(sessions):
            self._close_pdf_session(session, refresh=False)
        self.save_sessions()
        self._refresh_pdf_navigation()
        self._refresh_pdf_sidebar()

    def _on_pdf_tree_select(self, _event=None):
        if getattr(self, "_refreshing_pdf_sidebar", False):
            return
        tree = self.pdf_document_tree
        selected = tree.selection()
        if not selected:
            return
        selected_names = [item[4:] for item in selected if item.startswith("doc:")]
        _record_last_action("PDF sidebar selection", ", ".join(selected_names))
        try:
            document_count = len(selected_names)
            if hasattr(self, "pdf_selection_status"):
                self.pdf_selection_status.configure(
                    text=(f"{document_count} PDF selected" if document_count == 1
                          else f"{document_count} PDFs selected")
                )
            folder_items = [item for item in selected if item.startswith("folder:")]
            if folder_items:
                self.pdf_project["selected_folder_id"] = folder_items[0][7:]
                self.save_pdf_project()
                self.active_pdf_session = None
                if hasattr(self, "pdf_tabview") and "➕ New PDF" in getattr(self.pdf_tabview, "_tabs", {}):
                    self.pdf_tabview.set("➕ New PDF")

            _record_last_action("PDF sidebar selection complete", ", ".join(selected_names))
        except Exception as error:
            _write_handled_exception("PDF sidebar selection", error)
            debug(f"PDF sidebar selection failed: {error}", "error")
            try:
                messagebox.showerror(
                    "PDF Selection Error",
                    "CleanCutPDF could not open that document.\n\n"
                    f"Details saved to:\n{CRASH_FILE}"
                )
            except Exception:
                pass

    def _on_pdf_tree_double_click(self, event=None):
        """Open a PDF only after an explicit double-click."""
        tree = self.pdf_document_tree
        item_id = tree.identify_row(event.y) if event is not None else ""
        if not item_id or not item_id.startswith("doc:"):
            return
        session = self.pdf_sessions.get(item_id[4:])
        if session is not None:
            self._activate_pdf_session(session)

    def create_pdf_folder(self):
        name = simpledialog.askstring("New Folder", "Folder name:", parent=self)
        name = str(name or "").strip()
        if not name:
            return
        if any(folder.get("name", "").casefold() == name.casefold()
               for folder in self.pdf_project.get("folders", [])):
            messagebox.showinfo("Folder Exists", f"A folder named '{name}' already exists.")
            return
        folder_id = f"folder-{secrets.token_hex(6)}"
        self.pdf_project.setdefault("folders", []).append({
            "id": folder_id, "name": name, "parent_id": None
        })
        self.pdf_project["selected_folder_id"] = folder_id
        self.save_pdf_project()
        self._refresh_pdf_sidebar()

    def _selected_pdf_folder_for_action(self):
        """Return the explicitly selected sidebar folder for folder actions."""
        tree = getattr(self, "pdf_document_tree", None)
        if tree is not None:
            for item_id in tree.selection():
                if item_id.startswith("folder:"):
                    folder_id = item_id[7:]
                    if any(folder.get("id") == folder_id
                           for folder in self.pdf_project.get("folders", [])):
                        return folder_id
        return None

    def rename_pdf_folder(self):
        folder_id = self._selected_pdf_folder_for_action()
        if not folder_id:
            messagebox.showinfo("Rename Folder", "Select a folder first.")
            return
        if folder_id == "inbox":
            messagebox.showinfo("Rename Folder", "Inbox is the permanent default folder and cannot be renamed.")
            return

        folder = next(
            (item for item in self.pdf_project.get("folders", [])
             if item.get("id") == folder_id),
            None
        )
        if folder is None:
            return
        name = simpledialog.askstring(
            "Rename Folder", "New folder name:",
            initialvalue=folder.get("name", "Folder"), parent=self
        )
        name = str(name or "").strip()
        if not name:
            return
        if any(item.get("id") != folder_id
               and item.get("name", "").casefold() == name.casefold()
               for item in self.pdf_project.get("folders", [])):
            messagebox.showinfo("Folder Exists", f"A folder named '{name}' already exists.")
            return
        folder["name"] = name
        self.save_pdf_project()
        self._refresh_pdf_sidebar()
        debug(f"Renamed document folder: {folder_id} -> {name}", "saved")

    def delete_pdf_folder(self):
        folder_id = self._selected_pdf_folder_for_action()
        if not folder_id:
            messagebox.showinfo("Delete Folder", "Select a folder first.")
            return
        if folder_id == "inbox":
            messagebox.showinfo("Delete Folder", "Inbox is the permanent default folder and cannot be deleted.")
            return

        folder = next(
            (item for item in self.pdf_project.get("folders", [])
             if item.get("id") == folder_id),
            None
        )
        if folder is None:
            return
        document_count = sum(
            1 for session in self.pdf_sessions.values()
            if session.get("folder_id", "inbox") == folder_id
        )
        confirmation = (
            f"Delete the folder '{folder.get('name', 'Folder')}'?\n\n"
            f"{document_count} PDF(s) inside it will be moved to Inbox.\n"
            "The original PDF files on your computer will not be deleted."
        )
        if not messagebox.askyesno("Delete Folder", confirmation, parent=self):
            return

        for session in self.pdf_sessions.values():
            if session.get("folder_id", "inbox") == folder_id:
                session["folder_id"] = "inbox"
        self.pdf_project["folders"] = [
            item for item in self.pdf_project.get("folders", [])
            if item.get("id") != folder_id
        ]
        self.pdf_project["selected_folder_id"] = "inbox"
        self.save_pdf_project()
        self.save_sessions()
        self._refresh_pdf_sidebar()
        debug(f"Deleted document folder: {folder_id}; moved documents to Inbox", "saved")

    def move_pdf_folder(self, direction):
        folder_id = self._selected_pdf_folder_for_action()
        if not folder_id:
            messagebox.showinfo("Rearrange Folders", "Select a folder first.")
            return
        if folder_id == "inbox":
            messagebox.showinfo("Rearrange Folders", "Inbox stays first as the permanent default folder.")
            return

        folders = self.pdf_project.get("folders", [])
        current_index = next(
            (index for index, folder in enumerate(folders)
             if folder.get("id") == folder_id),
            None
        )
        if current_index is None:
            return
        target_index = current_index - 1 if direction == "up" else current_index + 1
        # Keep Inbox at the top of the folder list.
        if target_index < 1 or target_index >= len(folders):
            return
        folders[current_index], folders[target_index] = folders[target_index], folders[current_index]
        self.pdf_project["selected_folder_id"] = folder_id
        self.save_pdf_project()
        self._refresh_pdf_sidebar()
        tree = getattr(self, "pdf_document_tree", None)
        folder_item = f"folder:{folder_id}"
        if tree is not None and tree.exists(folder_item):
            tree.selection_set(folder_item)
        debug(f"Moved document folder {folder_id} {direction}", "saved")

    def _show_pdf_tree_context_menu(self, event):
        """Show file-explorer actions for the item under the pointer."""
        tree = getattr(self, "pdf_document_tree", None)
        if tree is None:
            return
        item_id = tree.identify_row(event.y)
        if not item_id:
            return

        # Right-clicking also makes the target the active selection, which
        # keeps folder actions predictable and supports document multi-select.
        if item_id.startswith("folder:"):
            tree.selection_set(item_id)
        elif item_id.startswith("doc:") and item_id not in tree.selection():
            tree.selection_set(item_id)
        tree.focus(item_id)

        menu = tk.Menu(self, tearoff=0)
        if item_id.startswith("folder:"):
            menu.add_command(label="New Folder", command=self.create_pdf_folder)
            menu.add_separator()
            menu.add_command(label="Rename Folder", command=self.rename_pdf_folder)
            menu.add_command(label="Delete Folder", command=self.delete_pdf_folder)
            menu.add_separator()
            menu.add_command(label="Move Folder Up", command=lambda: self.move_pdf_folder("up"))
            menu.add_command(label="Move Folder Down", command=lambda: self.move_pdf_folder("down"))
        else:
            menu.add_command(label="Change Workspace for Selected", command=self.bulk_change_workspace)
            menu.add_command(label="Move Selected to Folder", command=self._move_selected_documents_to_folder)
            menu.add_command(label="Close Selected PDF(s)", command=self.close_selected_documents)

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def bulk_change_workspace(self):
        sessions = self._selected_document_sessions()
        if not sessions:
            messagebox.showinfo("Change Workspace", "Select one or more PDFs first.")
            return

        available = list(WORKSPACES.keys()) or ["Accounting"]
        current = sessions[0].get("workspace", "Accounting")
        if current not in available:
            current = available[0]
        dialog = tk.Toplevel(self)
        dialog.title("Change Workspace")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        ctk.CTkLabel(
            dialog, text=f"Change workspace for {len(sessions)} document(s)",
            font=(self.font_family, self.font_size + 2, "bold")
        ).pack(padx=24, pady=(20, 10))
        workspace_var = ctk.StringVar(value=current)
        ctk.CTkOptionMenu(dialog, values=available, variable=workspace_var, width=230).pack(pady=8)

        def apply_change():
            workspace_name = workspace_var.get()
            for session in sessions:
                if session.get("is_rendered", False):
                    self.capture_workspace_data(session)
                session["workspace"] = workspace_name
            self.save_settings()
            self.save_sessions()
            self._update_pdf_sidebar_workspace_labels()
            active = self.get_active_session()
            if active in sessions and active.get("is_rendered", False):
                self.render_splitter_tab(active["tab"], active)
            dialog.destroy()
            debug(f"Bulk workspace switch: {len(sessions)} document(s) -> {workspace_name}", "saved")

        buttons = ctk.CTkFrame(dialog, fg_color="transparent")
        buttons.pack(fill="x", padx=20, pady=(12, 18))
        ctk.CTkButton(buttons, text="Cancel", width=100, command=dialog.destroy).pack(side="right", padx=(8, 0))
        ctk.CTkButton(buttons, text="Apply", width=100, command=apply_change).pack(side="right")
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        dialog.after(60, dialog.focus_force)

    def _move_selected_documents_to_folder(self):
        sessions = self._selected_document_sessions()
        if not sessions:
            return
        folder_names = [folder.get("name", "Folder") for folder in self.pdf_project.get("folders", [])]
        if not folder_names:
            return
        dialog = tk.Toplevel(self)
        dialog.title("Move Documents")
        dialog.transient(self)
        dialog.grab_set()
        ctk.CTkLabel(dialog, text=f"Move {len(sessions)} document(s) to:").pack(padx=20, pady=(18, 8))
        folder_var = ctk.StringVar(value=self._pdf_folder_name(self._selected_pdf_folder_id()))
        ctk.CTkOptionMenu(dialog, values=folder_names, variable=folder_var, width=220).pack(pady=8)

        def apply_move():
            target = next((folder.get("id") for folder in self.pdf_project.get("folders", [])
                           if folder.get("name") == folder_var.get()), "inbox")
            for session in sessions:
                session["folder_id"] = target
            self.save_sessions()
            self._refresh_pdf_sidebar()
            dialog.destroy()

        buttons = ctk.CTkFrame(dialog, fg_color="transparent")
        buttons.pack(fill="x", padx=20, pady=(12, 18))
        ctk.CTkButton(buttons, text="Cancel", width=100, command=dialog.destroy).pack(side="right", padx=(8, 0))
        ctk.CTkButton(buttons, text="Move", width=100, command=apply_move).pack(side="right")
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)

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
                "folder_id": session.get("folder_id", "inbox"),
                "detected_ranges": (
                    copy.deepcopy(session.get("ranges", []))
                    if session.get("ranges_ready", True) else []
                ),
                "file_signature": self._pdf_file_signature(session["path"]),
                "workspace_data": copy.deepcopy(session.get("workspace_data", {})),
                "parts": legacy_parts
            })

        _atomic_json_dump(SESSION_FILE, data)
        self.save_pdf_project()
        debug(f"Saved {len(data)} session(s) to {SESSION_FILE}", "saved")
    def _on_close(self):
        try:
            self.save_sessions()
            debug("Saving sessions", "debug")
        except Exception as error:
            debug(f"Could not save sessions during close: {error}", "error")
        finally:
            self.destroy()
    def reconcile_workspace_data_ranges(self, workspace_data, ranges):
        """Keep saved field values, but always trust the current PDF for part ranges."""
        if not isinstance(workspace_data, dict):
            return {}

        reconciled = {}
        for workspace_name, rows in workspace_data.items():
            if not isinstance(rows, list):
                continue
            new_rows = []
            for index, current_range in enumerate(ranges):
                row = {}
                if index < len(rows) and isinstance(rows[index], dict):
                    row.update(copy.deepcopy(rows[index]))
                row["range"] = copy.deepcopy(current_range)
                new_rows.append(row)
            reconciled[workspace_name] = new_rows
        return reconciled

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

            self.load_pdf_project()
            self.pdf_project["selected_folder_id"] = "inbox"
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
                if not workspace_data and legacy_parts:
                    workspace_data = {"Accounting": copy.deepcopy(legacy_parts)}

                if not path or not Path(path).exists():
                    continue

                pdf_name = Path(path).stem
                if pdf_name in self.pdf_sessions:
                    continue

                reader = PdfReader(path)
                cached_ranges = item.get("detected_ranges", [])
                cached_signature = item.get("file_signature")
                current_signature = self._pdf_file_signature(path)
                cache_is_valid = (
                    isinstance(cached_ranges, list)
                    and bool(cached_ranges)
                    and cached_signature == current_signature
                )

                tab_label = f"{pdf_name} ✖"
                tab = self.pdf_tabview.add(tab_label)
                session = {
                    "tab": tab,
                    "tab_label": tab_label,
                    "reader": reader,
                    "path": Path(path),
                    "folder_id": item.get("folder_id", "inbox"),
                    # Session restore is intentionally lazy. Detecting split
                    # markers and rendering previews for every saved PDF made
                    # startup scale linearly with the number of open files.
                    "ranges": copy.deepcopy(cached_ranges) if cache_is_valid else [],
                    "ranges_ready": cache_is_valid,
                    "entries": [],
                    "client_name_var": ctk.StringVar(value=client_name),
                    "workspace": workspace,
                    "workspace_data": copy.deepcopy(workspace_data),
                    "last_exported_files": [],
                    "widgets_to_scale": []
                }
                self.pdf_sessions[pdf_name] = session
                session["is_rendered"] = False
                self._render_pdf_placeholder(session)
                self._refresh_pdf_navigation()
            valid_folder_ids = {folder.get("id") for folder in self.pdf_project.get("folders", [])}
            for session in self.pdf_sessions.values():
                if session.get("folder_id") not in valid_folder_ids:
                    session["folder_id"] = "inbox"
            self._refresh_pdf_sidebar()
            # Restore the document list and folders, but do not open a PDF
            # editor automatically. Inbox is the initial landing view.
            self.active_pdf_session = None
            if "➕ New PDF" in getattr(self.pdf_tabview, "_tabs", {}):
                self.pdf_tabview.set("➕ New PDF")

        except Exception as e:
            messagebox.showwarning("Session Restore Failed", str(e))
            debug(f"Session restore error: {e}", "error")

    def check_future_date(self, raw_date, callback_on_confirm):
        try:
            today = datetime.date.today()
            entered_date = self.parse_flexible_date(raw_date)
        except Exception:
            debug(f"Invalid date format: {raw_date}", "debug")
            return

        if entered_date <= today or self.settings.get("suppressFutureDateWarning", False):
            callback_on_confirm()
            return

        popup = tk.Toplevel(self)
        bg_color = ctk.ThemeManager.theme["CTkFrame"]["fg_color"]
        if isinstance(bg_color, (list, tuple)):
            bg_color = bg_color[0] if ctk.get_appearance_mode() == "Light" else bg_color[1]
        popup.configure(bg=bg_color)
        popup.attributes("-topmost", True)
        popup.grab_set()
        popup.resizable(False, False)
        popup.geometry("380x175")
        popup.title("Confirm Future Date")

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

        def on_yes():
            if suppress_var.get():
                self.settings["suppressFutureDateWarning"] = True
                self.save_settings()
                if hasattr(self, "future_date_popup_var"):
                    self.future_date_popup_var.set(False)
            popup.destroy()
            callback_on_confirm()

        def on_cancel():
            popup.destroy()

        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.pack(pady=(0, 10))
        ctk.CTkButton(
            btn_frame, text="Yes", width=80,
            font=(self.font_family, self.font_size), command=on_yes
        ).pack(side="left", padx=10)
        ctk.CTkButton(
            btn_frame, text="Cancel", width=80,
            font=(self.font_family, self.font_size), command=on_cancel
        ).pack(side="left", padx=10)

    # ─── Tab Builders ───
    def build_splitter_tab(self):
        wrapper = ctk.CTkFrame(self.splitter_tab)
        wrapper.pack(fill="both", expand=True)

        self.splitter_wrapper = wrapper  # Store for access later

        # Enable drag-and-drop on wrapper
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.handle_drop)

        # Folder shortcuts stay available while processing a document, without
        # taking space away from the individual PDF tabs.
        self.folder_shortcut_bar = ctk.CTkFrame(wrapper, fg_color="transparent")
        self.folder_shortcut_bar.pack(fill="x", padx=10, pady=(8, 0))
        self.refresh_folder_shortcut_bar()
        self.pdf_sidebar_toggle_button = ctk.CTkButton(
            self.folder_shortcut_bar, text="◀ Hide Inbox", width=105,
            command=self.toggle_pdf_sidebar
        )
        self.pdf_sidebar_toggle_button.pack(side="right")

        self.load_pdf_project()
        # Inbox is always the landing folder when the application starts.
        self.pdf_project["selected_folder_id"] = "inbox"
        document_area = ctk.CTkFrame(wrapper, fg_color="transparent")
        document_area.pack(fill="both", expand=True, padx=8, pady=(6, 0))

        self.pdf_sidebar = ctk.CTkFrame(document_area, width=285, corner_radius=10)
        self.pdf_sidebar.pack(side="left", fill="y", padx=(0, 8))
        self.pdf_sidebar.pack_propagate(False)
        ctk.CTkLabel(
            self.pdf_sidebar, text="Documents",
            font=(self.font_family, max(11, self.font_size), "bold")
        ).pack(anchor="w", padx=12, pady=(10, 5))

        sidebar_buttons = ctk.CTkFrame(self.pdf_sidebar, fg_color="transparent")
        sidebar_buttons.pack(fill="x", padx=8, pady=(0, 6))
        ctk.CTkButton(
            sidebar_buttons, text="Open PDFs", width=82,
            command=self.load_pdf
        ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            sidebar_buttons, text="New Folder", width=86,
            command=self.create_pdf_folder
        ).pack(side="left", padx=4)

        self.pdf_selection_status = ctk.CTkLabel(
            self.pdf_sidebar,
            text="Click a PDF; Ctrl/Shift-click for multiple",
            font=(self.font_family, max(9, self.font_size - 3)),
            text_color="#888888"
        )
        self.pdf_selection_status.pack(anchor="w", padx=10, pady=(0, 5))

        tree_frame = ctk.CTkFrame(self.pdf_sidebar, fg_color="transparent")
        tree_frame.pack(fill="both", expand=True, padx=8, pady=(0, 6))
        tree_style = ttk.Style()
        try:
            if "clam" in tree_style.theme_names():
                tree_style.theme_use("clam")
            tree_dark = ctk.get_appearance_mode() == "Dark"
            tree_bg = "#2b2b2b" if tree_dark else "#f5f5f5"
            tree_fg = "#ffffff" if tree_dark else "#1e1e1e"
            tree_selected = "#3B8ED0"
            tree_font_size = max(9, min(12, self.font_size - 2))
            tree_style.configure(
                "CleanCutPDF.Treeview",
                rowheight=max(22, tree_font_size + 9),
                indent=10,
                font=(self.font_family, tree_font_size),
                background=tree_bg,
                fieldbackground=tree_bg,
                foreground=tree_fg
            )
            tree_style.map(
                "CleanCutPDF.Treeview",
                background=[("selected", tree_selected)],
                foreground=[("selected", "white")]
            )
            tree_style.configure(
                "CleanCutPDF.Treeview.Heading",
                font=(self.font_family, tree_font_size, "bold")
            )
        except tk.TclError:
            pass
        self.pdf_document_tree = ttk.Treeview(
            tree_frame, show="tree", selectmode="extended",
            style="CleanCutPDF.Treeview"
        )
        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.pdf_document_tree.yview)
        tree_scroll_x = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.pdf_document_tree.xview)
        self.pdf_document_tree.configure(
            yscrollcommand=tree_scroll.set,
            xscrollcommand=tree_scroll_x.set
        )
        # Use a grid for the explorer and its two scrollbars. Packing the
        # horizontal scrollbar after an expanding Treeview leaves only a tiny
        # sliver of usable width instead of spanning the explorer box.
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        self.pdf_document_tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll.grid(row=0, column=1, sticky="ns")
        tree_scroll_x.grid(row=1, column=0, sticky="ew")
        self.pdf_document_tree.bind("<<TreeviewSelect>>", self._on_pdf_tree_select)
        self.pdf_document_tree.bind("<Double-1>", self._on_pdf_tree_double_click)
        self.pdf_document_tree.bind("<Button-3>", self._show_pdf_tree_context_menu)

        ctk.CTkButton(
            self.pdf_sidebar, text="Change Workspace for Selected", height=32,
            command=self.bulk_change_workspace
        ).pack(fill="x", padx=8, pady=(0, 5))
        ctk.CTkButton(
            self.pdf_sidebar, text="Move Selected to Folder", height=30,
            command=self._move_selected_documents_to_folder
        ).pack(fill="x", padx=8, pady=(0, 8))
        ctk.CTkButton(
            self.pdf_sidebar, text="Close Selected PDF(s)", height=30,
            fg_color="#b84a4a", hover_color="#963b3b",
            command=self.close_selected_documents
        ).pack(fill="x", padx=8, pady=(0, 8))

        self.pdf_tabview = ctk.CTkTabview(document_area)
        self.pdf_tabview.pack(side="left", fill="both", expand=True)

        self.add_plus_tab()
        # The tabview remains as the internal editor container for backwards
        # compatibility, but document navigation is now handled by the sidebar.
        if hasattr(self.pdf_tabview, "_segmented_button"):
            self._hide_internal_pdf_tab_strip()
        self._apply_tab_font_size()
        self._refresh_pdf_sidebar()

    def toggle_pdf_sidebar(self):
        sidebar = getattr(self, "pdf_sidebar", None)
        if sidebar is None:
            return
        if sidebar.winfo_manager():
            sidebar.pack_forget()
            self.pdf_sidebar_toggle_button.configure(text="▶ Show Inbox")
        else:
            sidebar.pack(side="left", fill="y", padx=(0, 8), before=self.pdf_tabview)
            self.pdf_sidebar_toggle_button.configure(text="◀ Hide Inbox")

    def _hide_internal_pdf_tab_strip(self):
        """Hide the legacy PDF tab buttons while retaining their content frames."""
        segmented = getattr(self.pdf_tabview, "_segmented_button", None)
        if segmented is None:
            return
        for hide_method in ("pack_forget", "grid_forget", "place_forget"):
            try:
                getattr(segmented, hide_method)()
            except (tk.TclError, AttributeError):
                pass

    def _short_pdf_tab_label(self, index, internal_label):
        """Return a readable compact label while retaining the full key internally."""
        name = str(internal_label).removesuffix(" ✖")
        max_name_length = 24 if index < 10 else 21
        if len(name) > max_name_length:
            name = name[:max_name_length - 1].rstrip() + "…"
        return f"{index}. {name} ✖"

    def _refresh_pdf_navigation(self):
        """Keep PDF tab buttons compact and update the all-documents picker."""
        if not hasattr(self, "pdf_tabview"):
            return

        buttons = getattr(getattr(self.pdf_tabview, "_segmented_button", None), "_buttons_dict", {})
        sessions = list(getattr(self, "pdf_sessions", {}).items())
        display_values = []
        display_to_internal = {}

        for index, (base_name, session) in enumerate(sessions, start=1):
            internal_label = session.get("tab_label", f"{base_name} ✖")
            display_label = self._short_pdf_tab_label(index, internal_label)
            display_values.append(display_label)
            display_to_internal[display_label] = internal_label
            button = buttons.get(internal_label)
            if button is not None:
                try:
                    button.configure(text=display_label)
                except tk.TclError:
                    pass

        # Keep the special new-document tab short and visible.
        for special_label in ("➕ New PDF", "+"):
            button = buttons.get(special_label)
            if button is not None:
                try:
                    button.configure(text="➕ New PDF")
                except tk.TclError:
                    pass

        self._pdf_display_to_internal = display_to_internal
        if hasattr(self, "pdf_document_switcher"):
            values = display_values or ["No PDFs open"]
            self.pdf_document_switcher.configure(values=values)
            current_internal = self.pdf_tabview.get()
            current_display = next(
                (display for display, internal in display_to_internal.items() if internal == current_internal),
                values[0]
            )
            self.pdf_document_switcher_var.set(current_display)

    def _select_pdf_from_switcher(self, display_label):
        internal_label = getattr(self, "_pdf_display_to_internal", {}).get(display_label)
        if not internal_label:
            return
        try:
            self.pdf_tabview.set(internal_label)
            base_name = internal_label.removesuffix(" ✖")
            session = self.pdf_sessions.get(base_name)
            if session is not None:
                self._activate_pdf_session(session)
        except (KeyError, tk.TclError) as error:
            debug(f"Could not activate PDF from document picker: {error}", "error")

    def build_rename_only_tab(self):
        """Build the workspace-aware one-file-at-a-time rename editor."""
        self.rename_only_files = {}
        self.rename_only_selected_path = None
        wrapper = ctk.CTkFrame(self.rename_only_tab)
        wrapper.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            wrapper, text="📝 Rename Only",
            font=(self.font_family, self.font_size + 4, "bold"),
            text_color="#3B8ED0"
        ).pack(pady=(14, 3))
        ctk.CTkLabel(
            wrapper,
            text="Rename each PDF with the normal workspace fields. Each PDF is treated as one document; no SPLIT HERE markers are used.",
            wraplength=900,
            text_color="#888888"
        ).pack(pady=(0, 12))

        controls = ctk.CTkFrame(wrapper, fg_color="transparent")
        controls.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkButton(controls, text="➕ Add PDFs", command=self.add_rename_only_files, width=120).pack(side="left", padx=(0, 6))
        ctk.CTkButton(controls, text="Clear", command=self.clear_rename_only_files, width=80).pack(side="left", padx=6)
        ctk.CTkLabel(controls, text="Action:").pack(side="left", padx=(24, 6))
        self.rename_action_var = ctk.StringVar(value="Create renamed copies")
        ctk.CTkOptionMenu(
            controls,
            values=["Create renamed copies", "Rename originals in place"],
            variable=self.rename_action_var,
            width=190
        ).pack(side="left")

        destination_row = ctk.CTkFrame(wrapper, fg_color="transparent")
        destination_row.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkLabel(destination_row, text="Output folder:").pack(side="left", padx=(0, 8))
        self.rename_output_var = ctk.StringVar(value=self.settings.get("export_folder", ""))
        CTkEntry(destination_row, textvariable=self.rename_output_var).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(destination_row, text="Browse…", command=self.choose_rename_output_folder, width=90).pack(side="left")

        editor_area = ctk.CTkFrame(wrapper, fg_color="transparent")
        editor_area.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self.rename_rows_frame = ctk.CTkScrollableFrame(editor_area, width=245)
        self.rename_rows_frame.pack(side="left", fill="y", padx=(0, 10))
        self.rename_editor_frame = ctk.CTkFrame(editor_area)
        self.rename_editor_frame.pack(side="left", fill="both", expand=True)
        self.refresh_rename_only_rows()

    def add_rename_only_files(self):
        paths = filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
        changed = False
        for raw_path in paths:
            path = Path(raw_path)
            if path.suffix.lower() != ".pdf" or str(path) in self.rename_only_files:
                continue
            try:
                reader = PdfReader(str(path))
            except Exception as error:
                messagebox.showwarning("PDF Could Not Be Opened", f"{path.name}\n\n{error}")
                continue
            self.rename_only_files[str(path)] = {
                "path": path,
                "reader": reader,
                "ranges": [{"start": 0, "end": max(0, len(reader.pages) - 1)}],
                "ranges_ready": True,
                "entries": [],
                "client_name_var": ctk.StringVar(),
                "workspace": self.settings.get("default_workspace", "Accounting"),
                "workspace_data": {},
                "last_exported_files": [],
                "widgets_to_scale": [],
                "rename_only": True,
                "tab": self.rename_editor_frame,
                "tab_label": path.name
            }
            changed = True
        if changed:
            if self.rename_only_selected_path not in self.rename_only_files:
                self.rename_only_selected_path = next(iter(self.rename_only_files), None)
            self.refresh_rename_only_rows()
            self.select_rename_only_file(self.rename_only_selected_path)

    def clear_rename_only_files(self):
        self.rename_only_files.clear()
        self.rename_only_selected_path = None
        self.refresh_rename_only_rows()
        self._clear_rename_only_editor()

    def _clear_rename_only_editor(self):
        editor = getattr(self, "rename_editor_frame", None)
        if editor is None:
            return
        for child in editor.winfo_children():
            child.destroy()

    def choose_rename_output_folder(self):
        folder = filedialog.askdirectory(title="Select Rename Output Folder")
        if folder:
            self.rename_output_var.set(folder)

    def refresh_rename_only_rows(self):
        if not hasattr(self, "rename_rows_frame"):
            return
        for child in self.rename_rows_frame.winfo_children():
            child.destroy()

        if not self.rename_only_files:
            ctk.CTkLabel(
                self.rename_rows_frame,
                text="Add one or more PDFs to begin.", text_color="#888888"
            ).pack(pady=30)
        else:
            for path_string, session in self.rename_only_files.items():
                row = ctk.CTkFrame(self.rename_rows_frame)
                row.pack(fill="x", pady=3, padx=3)
                row.configure(fg_color="#3B8ED0" if path_string == self.rename_only_selected_path else "transparent")
                ctk.CTkButton(
                    row, text=Path(path_string).name, anchor="w", height=34,
                    fg_color="transparent", hover_color="#2f6f9f",
                    command=lambda item=path_string: self.select_rename_only_file(item)
                ).pack(side="left", fill="x", expand=True, padx=3, pady=3)
                ctk.CTkButton(
                    row, text="✕", width=32,
                    command=lambda item=path_string: self.remove_rename_only_file(item)
                ).pack(side="right", padx=(0, 3))

    def remove_rename_only_file(self, path_string):
        self.rename_only_files.pop(path_string, None)
        if self.rename_only_selected_path == path_string:
            self.rename_only_selected_path = next(iter(self.rename_only_files), None)
        self.refresh_rename_only_rows()
        if self.rename_only_selected_path:
            self.select_rename_only_file(self.rename_only_selected_path)
        else:
            self._clear_rename_only_editor()

    def select_rename_only_file(self, path_string):
        if not path_string or path_string not in self.rename_only_files:
            return
        self.rename_only_selected_path = path_string
        session = self.rename_only_files[path_string]
        session["tab"] = self.rename_editor_frame
        self.render_splitter_tab(self.rename_editor_frame, session)
        self.refresh_rename_only_rows()

    def rename_only_files_now(self):
        path_string = self.rename_only_selected_path
        if not path_string or path_string not in self.rename_only_files:
            messagebox.showinfo("Rename PDF", "Select a PDF first.")
            return
        session = self.rename_only_files[path_string]
        action = self.rename_action_var.get()
        output_folder = Path(self.rename_output_var.get().strip()).expanduser()
        if action == "Create renamed copies" and not output_folder:
            messagebox.showwarning("Output Folder Required", "Choose an output folder first.")
            return
        if action == "Rename originals in place" and not messagebox.askyesno(
            "Rename Originals", "This will change the original filenames. Continue?"
        ):
            return

        try:
            source = Path(session["path"])
            if not source.exists():
                raise FileNotFoundError(source)
            entry = session.get("entries", [None])[0]
            if entry is None:
                raise ValueError("The workspace fields have not finished loading yet.")
            new_stem = self.get_session_filename(session, entry)
            target_folder = source.parent if action == "Rename originals in place" else output_folder
            target_folder.mkdir(parents=True, exist_ok=True)
            target = target_folder / f"{new_stem}.pdf"
            counter = 2
            while target.exists() and target.resolve() != source.resolve():
                target = target_folder / f"{new_stem}_{counter}.pdf"
                counter += 1
            if action == "Rename originals in place":
                os.replace(source, target)
            else:
                shutil.copy2(source, target)

            messagebox.showinfo("Rename Complete", f"Saved as:\n{target.name}")
            debug(f"Rename-only completed: {source.name} -> {target.name}", "saved")
            self.remove_rename_only_file(path_string)
        except Exception as error:
            debug(f"Rename-only failed: {error}", "error")
            messagebox.showerror("Rename Failed", str(error))

    def open_folder_path(self, folder, label="Folder"):
        path = Path(str(folder or "")).expanduser()
        if not str(folder or "").strip():
            messagebox.showinfo("No Folder Set", f"Set the {label.lower()} first.")
            return
        if not path.is_dir():
            messagebox.showwarning("Folder Not Found", f"{label} no longer exists:\n\n{path}")
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as error:
            messagebox.showerror("Open Folder Failed", f"Could not open this folder:\n\n{error}")

    def refresh_folder_shortcut_bar(self):
        if not hasattr(self, "folder_shortcut_bar"):
            return
        for child in self.folder_shortcut_bar.winfo_children():
            child.destroy()

        ctk.CTkButton(
            self.folder_shortcut_bar, text="📁 Open Output Folder", width=165,
            command=lambda: self.open_folder_path(self.settings.get("export_folder", ""), "Default Export Folder")
        ).pack(side="left", padx=(0, 6))

        shortcuts = self.settings.get("folder_shortcuts", [])
        if not isinstance(shortcuts, list):
            shortcuts = []
        for shortcut in shortcuts:
            if not isinstance(shortcut, dict) or not shortcut.get("path"):
                continue
            label = str(shortcut.get("label") or Path(shortcut["path"]).name or "Folder")
            icon = str(shortcut.get("icon") or "📁").strip() or "📁"
            button_kwargs = {
                "text": f"{icon} {label}",
                "width": 130,
                "command": lambda item=shortcut: self.open_folder_path(
                    item.get("path"), item.get("label", "Folder")
                )
            }
            color = str(shortcut.get("color") or "").strip()
            if re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
                red, green, blue = (int(color[i:i + 2], 16) for i in (1, 3, 5))
                hover = "#{:02X}{:02X}{:02X}".format(
                    max(0, int(red * 0.82)),
                    max(0, int(green * 0.82)),
                    max(0, int(blue * 0.82))
                )
                text_color = "#000000" if (red * 299 + green * 587 + blue * 114) > 150000 else "#FFFFFF"
                button_kwargs.update(fg_color=color, hover_color=hover, text_color=text_color)
            ctk.CTkButton(self.folder_shortcut_bar, **button_kwargs).pack(side="left", padx=3)

        ctk.CTkButton(
            self.folder_shortcut_bar, text="Manage Folders…", width=125,
            command=self.manage_folder_shortcuts
        ).pack(side="right")

    def manage_folder_shortcuts(self):
        popup = tk.Toplevel(self)
        popup.title("Manage Folder Shortcuts")
        popup.transient(self)
        popup.geometry("600x420")
        popup.minsize(500, 300)

        ctk.CTkLabel(
            popup, text="Folder Shortcuts", font=(self.font_family, self.font_size + 3, "bold")
        ).pack(anchor="w", padx=16, pady=(16, 3))
        ctk.CTkLabel(
            popup, text="Add folders you open often, such as Files to be Processed or a mail log folder.",
            text_color="#888888", wraplength=550, justify="left"
        ).pack(anchor="w", padx=16, pady=(0, 10))

        listing = ctk.CTkScrollableFrame(popup)
        listing.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        def redraw():
            for child in listing.winfo_children():
                child.destroy()
            items = self.settings.get("folder_shortcuts", [])
            for index, item in enumerate(items):
                if not isinstance(item, dict):
                    continue
                row = ctk.CTkFrame(listing)
                row.pack(fill="x", pady=4)
                label = item.get("label") or Path(item.get("path", "")).name or "Folder"
                icon = str(item.get("icon") or "📁").strip() or "📁"
                label_kwargs = {
                    "text": f"{icon}  {label}\n{item.get('path', '')}",
                    "justify": "left",
                    "anchor": "w"
                }
                color = str(item.get("color") or "").strip()
                if re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
                    label_kwargs["text_color"] = color
                ctk.CTkLabel(row, **label_kwargs).pack(
                    side="left", fill="x", expand=True, padx=10, pady=7
                )
                ctk.CTkButton(row, text="Open", width=62, command=lambda value=item: self.open_folder_path(value.get("path"), value.get("label", "Folder"))).pack(side="right", padx=4)
                ctk.CTkButton(row, text="Edit", width=62, command=lambda i=index: edit_shortcut(i)).pack(side="right", padx=4)
                ctk.CTkButton(row, text="Remove", width=75, fg_color="#B33A3A", hover_color="#8D2D2D",
                              command=lambda i=index: remove(i)).pack(side="right", padx=(4, 8))

        def edit_shortcut(index, remove_if_cancelled=False):
            items = self.settings.get("folder_shortcuts", [])
            if not (0 <= index < len(items)):
                return
            item = items[index]

            editor = tk.Toplevel(popup)
            editor.title("Edit Folder Shortcut")
            editor.transient(popup)
            editor.grab_set()
            editor.resizable(False, False)
            editor.geometry("470x300")

            ctk.CTkLabel(
                editor, text="Folder Shortcut",
                font=(self.font_family, self.font_size + 2, "bold")
            ).pack(anchor="w", padx=18, pady=(16, 10))

            form = ctk.CTkFrame(editor, fg_color="transparent")
            form.pack(fill="x", padx=18)
            ctk.CTkLabel(form, text="Name", width=80, anchor="w").grid(row=0, column=0, sticky="w", pady=6)
            label_var = ctk.StringVar(value=item.get("label") or Path(item.get("path", "")).name)
            CTkEntry(form, textvariable=label_var, width=330).grid(row=0, column=1, sticky="ew", pady=6)

            ctk.CTkLabel(form, text="Icon", width=80, anchor="w").grid(row=1, column=0, sticky="w", pady=6)
            icon_var = ctk.StringVar(value=str(item.get("icon") or "📁"))
            ctk.CTkOptionMenu(
                form,
                values=["📁", "📂", "🗂️", "📥", "📤", "📌", "⭐", "⚡", "🧾", "💼"],
                variable=icon_var,
                width=120
            ).grid(row=1, column=1, sticky="w", pady=6)

            ctk.CTkLabel(form, text="Color", width=80, anchor="w").grid(row=2, column=0, sticky="w", pady=6)
            color_var = ctk.StringVar(value=str(item.get("color") or ""))
            color_row = ctk.CTkFrame(form, fg_color="transparent")
            color_row.grid(row=2, column=1, sticky="ew", pady=6)
            color_entry = CTkEntry(color_row, textvariable=color_var, width=190)
            color_entry.pack(side="left")

            def choose_color():
                chosen = colorchooser.askcolor(color=color_var.get() or None, parent=editor)[1]
                if chosen:
                    color_var.set(chosen.upper())

            ctk.CTkButton(color_row, text="Choose…", width=90, command=choose_color).pack(side="left", padx=8)
            ctk.CTkLabel(
                editor, text=str(item.get("path", "")),
                text_color="#888888", wraplength=420, justify="left"
            ).pack(anchor="w", padx=18, pady=(8, 4))

            def cancel():
                if remove_if_cancelled and 0 <= index < len(items):
                    items.pop(index)
                editor.destroy()
                redraw()

            def save():
                label = label_var.get().strip() or Path(item.get("path", "")).name or "Folder"
                raw_color = color_var.get().strip()
                try:
                    color = self.normalize_field_color(raw_color) if raw_color else ""
                except ValueError as error:
                    messagebox.showerror("Invalid Color", str(error), parent=editor)
                    return
                item.update({"label": label, "icon": icon_var.get().strip() or "📁", "color": color})
                self.save_settings()
                self.refresh_folder_shortcut_bar()
                editor.destroy()
                redraw()

            buttons = ctk.CTkFrame(editor, fg_color="transparent")
            buttons.pack(fill="x", padx=18, pady=(12, 16))
            ctk.CTkButton(buttons, text="Cancel", width=90, command=cancel).pack(side="right", padx=(6, 0))
            ctk.CTkButton(buttons, text="Save", width=90, command=save).pack(side="right")
            editor.protocol("WM_DELETE_WINDOW", cancel)

        def remove(index):
            items = self.settings.get("folder_shortcuts", [])
            if 0 <= index < len(items):
                items.pop(index)
                self.save_settings()
                self.refresh_folder_shortcut_bar()
                redraw()

        def add_folder():
            path = filedialog.askdirectory(parent=popup, title="Choose Shortcut Folder")
            if not path:
                return
            items = self.settings.setdefault("folder_shortcuts", [])
            items.append({"label": Path(path).name, "path": path, "icon": "📁", "color": ""})
            edit_shortcut(len(items) - 1, remove_if_cancelled=True)

        buttons = ctk.CTkFrame(popup, fg_color="transparent")
        buttons.pack(fill="x", padx=16, pady=(0, 14))
        ctk.CTkButton(buttons, text="+ Add Folder", command=add_folder).pack(side="left")
        ctk.CTkButton(buttons, text="Done", command=popup.destroy).pack(side="right")
        redraw()
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
            "• Files are auto-split and named using your Quick Split filename-order setting",
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

        for section in ["Appearance", "Export", "Behavior", "Workspaces", "Custom Fields", "License"]:
            # Behavior contains more controls than can fit vertically at larger
            # font sizes, so make the SECTION ITSELF scrollable. This is more
            # reliable than placing a second canvas inside a hidden settings
            # frame because CTkScrollableFrame owns the viewport and scrollbar.
            if section == "Behavior":
                frame = ctk.CTkScrollableFrame(
                    self.settings_stack,
                    fg_color="transparent",
                    corner_radius=0
                )
                self.behavior_settings_frame = frame
            else:
                frame = ctk.CTkFrame(self.settings_stack)
            frame.pack(fill="both", expand=True)
            frame.pack_forget()  # Hide initially
            self.settings_sections[section] = frame

        # Populate each section
        self._build_appearance_section(self.settings_sections["Appearance"])
        self._build_export_section(self.settings_sections["Export"])
        self._build_behavior_section(self.settings_sections["Behavior"])
        self._build_workspaces_section(self.settings_sections["Workspaces"])
        self._build_custom_fields_section(self.settings_sections["Custom Fields"])
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
        self.log_filters = {"workspace": "", "date_from": "", "date_to": ""}

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
        self.log_filter_button = ctk.CTkButton(search_frame, text="⚲ Filters", command=self.open_log_filters)
        self.log_filter_button.pack(side="right", padx=(10, 0))

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

        ctk.CTkLabel(bubble2, text="Filename order is configurable in Settings > Behavior > Quick Split.", font=font_code).pack(anchor="w", padx=label_padx + 25)
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
                session["is_rendered"] = False
                self._render_pdf_placeholder(session)

            self._refresh_pdf_sidebar()
            self._apply_font_size()
            self._apply_tab_font_size()
            self.enable_tab_closing()

            self.active_pdf_session = None
            if "➕ New PDF" in getattr(self.pdf_tabview, "_tabs", {}):
                self.pdf_tabview.set("➕ New PDF")

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
        """Build Behavior settings directly inside its scrollable section."""
        font = (self.font_family, self.font_size)
        bubble_color, border_color = self.get_log_bubble_colors()

        # `parent` is a CTkScrollableFrame created by build_settings_tab().
        # All Behavior cards must be children of this frame so its native
        # scrollbar scrolls the ITEMS themselves.
        scroll = parent

        # ─── File Processing ───
        file_bubble = ctk.CTkFrame(scroll, fg_color=bubble_color, border_color=border_color, border_width=2, corner_radius=10)
        file_bubble.pack(padx=10, pady=(15, 10), fill="x")

        ctk.CTkLabel(file_bubble, text="🗂 File Processing", font=(self.font_family, self.font_size + 2, "bold")).pack(anchor="w", padx=15, pady=(10, 5))

        self.remove_blank_var = ctk.BooleanVar(value=self.settings.get("remove_blank_pages", True))
        blank_checkbox = ctk.CTkCheckBox(file_bubble, text="Remove Blank Pages Automatically", variable=self.remove_blank_var, command=self.update_remove_blank_setting)
        blank_checkbox.pack(anchor="w", padx=20, pady=5)
        self.settings_widgets_to_scale.append(blank_checkbox)
        ctk.CTkLabel(
            file_bubble,
            text="Checks every exported page, including blank pages between non-blank pages.",
            font=(self.font_family, max(10, self.font_size - 2)),
            text_color="#888888",
            wraplength=700,
            justify="left"
        ).pack(anchor="w", padx=40, pady=(0, 4))

        ctk.CTkLabel(
            file_bubble,
            text="Field defaults, required rules, autofill, choices, date formats, and conditions are configured in Settings > Custom Fields.",
            font=(self.font_family, max(10, self.font_size - 1)),
            text_color="#888888",
            wraplength=700,
            justify="left"
        ).pack(anchor="w", padx=20, pady=(6, 10))

        # ─── Startup Behavior ───
        startup_bubble = ctk.CTkFrame(scroll, fg_color=bubble_color, border_color=border_color, border_width=2, corner_radius=10)
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
        date_bubble = ctk.CTkFrame(scroll, fg_color=bubble_color, border_color=border_color, border_width=2, corner_radius=10)
        date_bubble.pack(padx=10, pady=(0, 10), fill="x")

        ctk.CTkLabel(date_bubble, text="📅 Date Options", font=(self.font_family, self.font_size + 2, "bold")).pack(anchor="w", padx=15, pady=(10, 5))

        ctk.CTkLabel(
            date_bubble,
            text="Choose whether a Date field starts with today's date in that field's Custom Field settings.",
            text_color="#888888", wraplength=700, justify="left"
        ).pack(anchor="w", padx=20, pady=(0, 5))

        self.future_date_popup_var = ctk.BooleanVar(value=not self.settings.get("suppressFutureDateWarning", False))
        future_checkbox = ctk.CTkCheckBox(date_bubble, text="Warn me when I enter a future date", variable=self.future_date_popup_var, command=self.update_future_date_setting)
        future_checkbox.pack(anchor="w", padx=20, pady=(0, 10))
        self.settings_widgets_to_scale.append(future_checkbox)

        # ─── Quick Split ───
        quick_split_bubble = ctk.CTkFrame(scroll, fg_color=bubble_color, border_color=border_color, border_width=2, corner_radius=10)
        quick_split_bubble.pack(padx=10, pady=(0, 10), fill="x")

        ctk.CTkLabel(
            quick_split_bubble, text="⚡ Quick Split",
            font=(self.font_family, self.font_size + 2, "bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))

        ctk.CTkLabel(
            quick_split_bubble, text="Filename order:",
            font=(self.font_family, self.font_size)
        ).pack(anchor="w", padx=20, pady=(0, 4))

        saved_quick_order = self.settings.get("quick_split_filename_order", QUICK_SPLIT_FILENAME_ORDERS[0])
        if saved_quick_order not in QUICK_SPLIT_FILENAME_ORDERS:
            saved_quick_order = QUICK_SPLIT_FILENAME_ORDERS[0]
        self.quick_split_filename_order_var = ctk.StringVar(value=saved_quick_order)
        quick_order_menu = ctk.CTkOptionMenu(
            quick_split_bubble,
            values=QUICK_SPLIT_FILENAME_ORDERS,
            variable=self.quick_split_filename_order_var,
            command=self.update_quick_split_filename_order
        )
        quick_order_menu.pack(anchor="w", padx=20, pady=(0, 10))
        self.settings_widgets_to_scale.append(quick_order_menu)

        # ─── Split Detection Warning ───
        split_warning_bubble = ctk.CTkFrame(scroll, fg_color=bubble_color, border_color=border_color, border_width=2, corner_radius=10)
        split_warning_bubble.pack(padx=10, pady=(0, 10), fill="x")

        ctk.CTkLabel(
            split_warning_bubble,
            text="✂ Split Detection Warnings",
            font=(self.font_family, self.font_size + 2, "bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))

        self.no_split_warning_var = ctk.BooleanVar(
            value=not self.settings.get("suppressNoSplitWarning", False)
        )
        no_split_checkbox = ctk.CTkCheckBox(
            split_warning_bubble,
            text="Warn me when no SPLIT HERE pages are detected",
            variable=self.no_split_warning_var,
            command=self.update_no_split_warning_setting
        )
        no_split_checkbox.pack(anchor="w", padx=20, pady=(0, 10))
        self.settings_widgets_to_scale.append(no_split_checkbox)

        # ─── Tools ───
        tools_bubble = ctk.CTkFrame(scroll, fg_color=bubble_color, border_color=border_color, border_width=2, corner_radius=10)
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

        reset_btn = ctk.CTkButton(
            tools_bubble,
            text="Reset Settings to Defaults",
            fg_color="#cc4b4b",
            hover_color="#aa2b2b",
            text_color="#ffffff",
            command=self.open_settings_reset_captcha
        )
        reset_btn.pack(anchor="w", padx=15, pady=(0, 10))
        self.settings_widgets_to_scale.append(reset_btn)

    def open_settings_reset_captcha(self):
        """Require a short CAPTCHA before resetting application settings."""
        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        captcha_code = "".join(secrets.choice(alphabet) for _ in range(6))

        popup = tk.Toplevel(self)
        popup.title("Reset Settings")
        popup.transient(self)
        popup.grab_set()
        popup.resizable(False, False)
        popup.attributes("-topmost", True)

        width = 500
        height = 330
        self.update_idletasks()
        x = self.winfo_rootx() + max(0, (self.winfo_width() - width) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - height) // 2)
        popup.geometry(f"{width}x{height}+{x}+{y}")

        bubble_color, border_color = self.get_log_bubble_colors()
        root_frame = ctk.CTkFrame(popup, fg_color=bubble_color, border_color=border_color, border_width=2)
        root_frame.pack(fill="both", expand=True, padx=14, pady=14)

        ctk.CTkLabel(
            root_frame,
            text="Reset CleanCutPDF Settings?",
            font=(self.font_family, self.font_size + 3, "bold")
        ).pack(pady=(18, 8))

        ctk.CTkLabel(
            root_frame,
            text=(
                "This resets the main settings.json file, including themes, export settings, "
                "workspaces, custom fields, and behavior options.\n\n"
                "Your license, logs, saved sessions, and keybinds are not deleted."
            ),
            font=(self.font_family, max(10, self.font_size - 1)),
            text_color="#aaaaaa",
            wraplength=430,
            justify="center"
        ).pack(padx=20, pady=(0, 12))

        ctk.CTkLabel(
            root_frame,
            text="Type this code to continue:",
            font=(self.font_family, self.font_size)
        ).pack(pady=(0, 5))

        # Space the characters to make the challenge easy to read but difficult
        # to confirm accidentally.
        ctk.CTkLabel(
            root_frame,
            text="  ".join(captcha_code),
            font=("Consolas", self.font_size + 6, "bold")
        ).pack(pady=(0, 8))

        captcha_var = ctk.StringVar()
        captcha_entry = CTkEntry(root_frame, textvariable=captcha_var, width=230, justify="center")
        captcha_entry.pack(pady=(0, 12))

        status_var = ctk.StringVar(value="")
        status_label = ctk.CTkLabel(
            root_frame,
            textvariable=status_var,
            text_color="#ff6b6b",
            font=(self.font_family, max(10, self.font_size - 1))
        )
        status_label.pack(pady=(0, 5))

        button_row = ctk.CTkFrame(root_frame, fg_color="transparent")
        button_row.pack(pady=(0, 14))

        def attempt_reset():
            entered = captcha_var.get().strip().upper()
            if entered != captcha_code:
                status_var.set("CAPTCHA does not match.")
                captcha_var.set("")
                captcha_entry.focus_set()
                self.bell()
                return

            try:
                popup.grab_release()
            except tk.TclError:
                pass
            popup.destroy()
            self.reset_main_settings_to_defaults()

        ctk.CTkButton(
            button_row,
            text="Cancel",
            width=110,
            command=popup.destroy
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            button_row,
            text="Reset Settings",
            width=130,
            fg_color="#cc4b4b",
            hover_color="#aa2b2b",
            text_color="#ffffff",
            command=attempt_reset
        ).pack(side="left", padx=6)

        captcha_entry.bind("<Return>", lambda _event: attempt_reset())
        popup.protocol("WM_DELETE_WINDOW", popup.destroy)
        popup.after(80, captcha_entry.focus_force)

    def reset_main_settings_to_defaults(self):
        """Reset settings.json only; leave license and other user data intact."""
        try:
            self.settings = copy.deepcopy(DEFAULT_SETTINGS)
            self.rebuild_runtime_workspaces()
            self.save_settings()
            debug("Main settings reset to defaults. License and other user data preserved.", "saved")
        except Exception as error:
            debug(f"Failed to reset settings: {error}", "error")
            messagebox.showerror(
                "Reset Failed",
                f"CleanCutPDF could not reset the settings file:\n\n{error}"
            )
            return

        messagebox.showinfo(
            "Settings Reset",
            "The main CleanCutPDF settings were reset to their defaults.\n\n"
            "Your license, logs, saved sessions, and keybinds were left unchanged.\n\n"
            "CleanCutPDF will now restart so all defaults take effect."
        )
        self.restart_after_settings_reset()

    def restart_after_settings_reset(self):
        """Restart the current development script or compiled executable."""
        try:
            self.save_sessions()
        except Exception as error:
            debug(f"Could not save sessions before settings-reset restart: {error}", "warning")

        try:
            if getattr(sys, "frozen", False):
                subprocess.Popen([sys.executable])
            else:
                subprocess.Popen([sys.executable, str(Path(__file__).resolve())])
        except Exception as error:
            debug(f"Automatic restart after settings reset failed: {error}", "error")
            messagebox.showwarning(
                "Restart Required",
                "Settings were reset successfully, but CleanCutPDF could not restart automatically.\n\n"
                "Please close and reopen the app."
            )
            return

        self.destroy()

    def _build_workspaces_section(self, parent):
        # The workspace editor can grow substantially (especially the visual
        # filename builder), so keep the entire section vertically scrollable.
        scroll = ctk.CTkScrollableFrame(parent)
        scroll.pack(fill="both", expand=True, padx=8, pady=8)
        self.workspaces_scroll = scroll

        bubble_color, border_color = self.get_log_bubble_colors()

        selector_bubble = ctk.CTkFrame(
            scroll, fg_color=bubble_color, border_color=border_color,
            border_width=2, corner_radius=10
        )
        selector_bubble.pack(padx=10, pady=(15, 10), fill="x")

        ctk.CTkLabel(
            selector_bubble,
            text="🗂 Workspace Profiles",
            font=(self.font_family, self.font_size + 2, "bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))

        ctk.CTkLabel(
            selector_bubble,
            text=(
                "Accounting is permanent. Other workspaces can be created, renamed, or deleted. "
                "For normal field ordering, use the drag-and-drop Assigned list in Custom Fields. "
                "Use Advanced Layout only when you need custom sizing or positioning."
            ),
            font=(self.font_family, max(10, self.font_size - 1)),
            text_color="#888888", wraplength=720, justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 8))

        row = ctk.CTkFrame(selector_bubble, fg_color="transparent")
        row.pack(fill="x", padx=15, pady=(0, 12))

        selected = self.settings.get("default_workspace", "Accounting")
        if selected not in WORKSPACES:
            selected = "Accounting"
        self.workspace_settings_selector_var = ctk.StringVar(value=selected)
        self.workspace_settings_selector = ctk.CTkOptionMenu(
            row, values=list(WORKSPACES.keys()),
            variable=self.workspace_settings_selector_var,
            command=self.refresh_workspace_settings_editor,
            width=190
        )
        self.workspace_settings_selector.pack(side="left", padx=(0, 8))

        ctk.CTkButton(row, text="+ New", width=85, command=self.create_workspace).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Rename", width=85, command=self.rename_selected_workspace).pack(side="left", padx=4)
        ctk.CTkButton(
            row, text="Delete", width=85, fg_color="#cc4b4b", hover_color="#aa2b2b",
            command=self.delete_selected_workspace
        ).pack(side="left", padx=4)

        self.workspace_settings_editor = ctk.CTkFrame(scroll, fg_color="transparent")
        self.workspace_settings_editor.pack(fill="x", expand=True, padx=10, pady=(0, 20))
        self.refresh_workspace_settings_editor(selected)

    def create_workspace(self):
        name = simpledialog.askstring("New Workspace", "Workspace name:", parent=self)
        if not name:
            return
        name = name.strip()
        if not name:
            return
        if name in self.settings.get("workspaces", {}):
            messagebox.showerror("Workspace Exists", f"A workspace named '{name}' already exists.")
            return

        self.settings.setdefault("workspaces", {})[name] = {
            "client_label": "Client Name",
            "summary": "Custom document workflow.",
            "filename_template": "{client}_{date}",
            "field_keys": [],
            "field_overrides": {},
            "notes": [],
            "custom_layout": None,
            "permanent": False
        }
        self.settings["default_workspace"] = name
        self.rebuild_runtime_workspaces()
        self.save_settings()
        self.rebuild_ui()
        self.notebook.set("Settings")
        self._show_settings_section("Workspaces")
        self.workspace_settings_selector_var.set(name)
        self.refresh_workspace_settings_editor(name)

    def rename_selected_workspace(self):
        old_name = self.workspace_settings_selector_var.get()
        definition = self.settings.get("workspaces", {}).get(old_name, {})
        if definition.get("permanent") or old_name == "Accounting":
            messagebox.showinfo("Permanent Workspace", "Accounting cannot be renamed.")
            return

        new_name = simpledialog.askstring(
            "Rename Workspace", "New workspace name:", initialvalue=old_name, parent=self
        )
        if not new_name:
            return
        new_name = new_name.strip()
        if not new_name or new_name == old_name:
            return
        if new_name in self.settings.get("workspaces", {}):
            messagebox.showerror("Workspace Exists", f"A workspace named '{new_name}' already exists.")
            return

        workspaces = self.settings["workspaces"]
        workspaces[new_name] = workspaces.pop(old_name)

        if self.settings.get("default_workspace") == old_name:
            self.settings["default_workspace"] = new_name

        for session in self.pdf_sessions.values():
            if session.get("workspace") == old_name:
                session["workspace"] = new_name
            data = session.get("workspace_data", {})
            if old_name in data:
                data[new_name] = data.pop(old_name)

        self.rebuild_runtime_workspaces()
        self.save_settings()
        self.rebuild_ui()
        self.notebook.set("Settings")
        self._show_settings_section("Workspaces")
        self.workspace_settings_selector_var.set(new_name)
        self.refresh_workspace_settings_editor(new_name)

    def delete_selected_workspace(self):
        name = self.workspace_settings_selector_var.get()
        definition = self.settings.get("workspaces", {}).get(name, {})
        if definition.get("permanent") or name == "Accounting":
            messagebox.showinfo("Permanent Workspace", "Accounting cannot be deleted.")
            return
        if not messagebox.askyesno("Delete Workspace", f"Delete the '{name}' workspace?"):
            return

        self.settings.get("workspaces", {}).pop(name, None)
        self.settings.get("workspace_settings", {}).pop(name, None)
        if self.settings.get("default_workspace") == name:
            self.settings["default_workspace"] = "Accounting"

        for session in self.pdf_sessions.values():
            if session.get("workspace") == name:
                self.capture_workspace_data(session)
                session["workspace"] = "Accounting"
            session.get("workspace_data", {}).pop(name, None)

        self.rebuild_runtime_workspaces()
        self.save_settings()
        self.rebuild_ui()
        self.notebook.set("Settings")
        self._show_settings_section("Workspaces")

    def refresh_workspace_settings_editor(self, workspace_name):
        if workspace_name not in WORKSPACES:
            workspace_name = "Accounting"
        self.workspace_settings_selector_var.set(workspace_name)
        self.settings["default_workspace"] = workspace_name

        for child in self.workspace_settings_editor.winfo_children():
            child.destroy()

        bubble_color, border_color = self.get_log_bubble_colors()
        profile = self.get_workspace_profile(workspace_name)
        definition = self.settings["workspaces"][workspace_name]

        profile_bubble = ctk.CTkFrame(
            self.workspace_settings_editor, fg_color=bubble_color,
            border_color=border_color, border_width=2, corner_radius=10
        )
        profile_bubble.pack(fill="x")

        permanent_text = " (Permanent)" if definition.get("permanent") else ""
        ctk.CTkLabel(
            profile_bubble,
            text=f"{workspace_name} Workspace{permanent_text}",
            font=(self.font_family, self.font_size + 2, "bold")
        ).pack(anchor="w", padx=15, pady=(12, 6))

        ctk.CTkLabel(profile_bubble, text="Client field label").pack(anchor="w", padx=15)
        client_label_var = ctk.StringVar(value=definition.get("client_label", "Client Name"))
        client_entry = CTkEntry(profile_bubble, textvariable=client_label_var)
        client_entry.pack(fill="x", padx=15, pady=(0, 8))

        ctk.CTkLabel(profile_bubble, text="Workspace description").pack(anchor="w", padx=15)
        summary_var = ctk.StringVar(value=definition.get("summary", ""))
        summary_entry = CTkEntry(profile_bubble, textvariable=summary_var)
        summary_entry.pack(fill="x", padx=15, pady=(0, 8))

        def save_profile_text(_event=None):
            definition["client_label"] = client_label_var.get().strip() or "Client Name"
            definition["summary"] = summary_var.get().strip() or "Custom document workflow."
            self.rebuild_runtime_workspaces()
            self.save_settings()

        client_entry.bind("<FocusOut>", save_profile_text)
        client_entry.bind("<Return>", save_profile_text)
        summary_entry.bind("<FocusOut>", save_profile_text)
        summary_entry.bind("<Return>", save_profile_text)

        ctk.CTkLabel(profile_bubble, text="Filename / Title Format").pack(anchor="w", padx=15, pady=(5, 2))
        self.build_visual_filename_editor(
            profile_bubble,
            workspace_name,
            definition.get("filename_template", profile["default_filename_template"])
        )

        self.build_workspace_notes_editor(profile_bubble, workspace_name, definition)

        layout_row = ctk.CTkFrame(profile_bubble, fg_color="transparent")
        layout_row.pack(fill="x", padx=15, pady=(2, 10))
        custom_layout = definition.get("custom_layout")
        layout_status = "Custom layout active" if isinstance(custom_layout, dict) and custom_layout.get("enabled") else "Automatic layout"
        ctk.CTkLabel(
            layout_row, text=f"Advanced layout: {layout_status}",
            font=(self.font_family, max(10, self.font_size - 1)),
            text_color="#888888"
        ).pack(side="left")
        ctk.CTkButton(
            layout_row, text="Advanced Layout...", width=135,
            command=lambda wn=workspace_name: self.open_workspace_layout_designer(wn)
        ).pack(side="right", padx=(8, 0))
        if isinstance(custom_layout, dict) and custom_layout.get("enabled"):
            ctk.CTkButton(
                layout_row, text="Reset to Automatic", width=135,
                fg_color="#cc4b4b", hover_color="#aa2b2b",
                command=lambda wn=workspace_name: self.reset_workspace_layout(wn)
            ).pack(side="right")

        field_names = ", ".join(field["label"] for field in profile.get("fields", [])) or "No fields assigned"
        ctk.CTkLabel(
            profile_bubble,
            text=f"Assigned fields: {field_names}\nManage assignments and order in Settings > Custom Fields.",
            font=(self.font_family, max(10, self.font_size - 2)),
            text_color="#888888", wraplength=700, justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 12))
        self.save_settings()

    def build_workspace_notes_editor(self, parent, workspace_name, definition):
        """Let a workspace place reusable reminder text between its fields."""
        profile = self.get_workspace_profile(workspace_name)
        notes = definition.setdefault("notes", [])

        separator = ctk.CTkFrame(parent, height=1, fg_color="#777777")
        separator.pack(fill="x", padx=15, pady=(6, 10))

        heading_row = ctk.CTkFrame(parent, fg_color="transparent")
        heading_row.pack(fill="x", padx=15, pady=(0, 4))
        ctk.CTkLabel(
            heading_row,
            text="Workspace Notes / Reminders",
            font=(self.font_family, self.font_size, "bold")
        ).pack(side="left")

        ctk.CTkButton(
            heading_row,
            text="+ Add Note",
            width=95,
            command=lambda: self.add_workspace_note(workspace_name)
        ).pack(side="right")

        ctk.CTkLabel(
            parent,
            text=(
                "Add italic reminders that appear inside every part. Choose whether each note "
                "appears at the top, directly below a specific field title, or at the end."
            ),
            font=(self.font_family, max(10, self.font_size - 2)),
            text_color="#888888",
            wraplength=700,
            justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 7))

        standard_fields = [
            field for field in profile.get("fields", [])
            if field.get("placement") != "header"
        ]
        position_pairs = [("Top of each part", "__top__")]
        position_pairs.extend(
            (f"Below title: {field.get('label', field.get('key', 'Field'))}", field.get("key"))
            for field in standard_fields
            if field.get("key")
        )
        position_pairs.append(("End of each part", "__end__"))
        label_to_position = {label: value for label, value in position_pairs}
        position_to_label = {value: label for label, value in position_pairs}
        position_labels = [label for label, _value in position_pairs]

        if not notes:
            ctk.CTkLabel(
                parent,
                text="No workspace notes yet.",
                text_color="#888888",
                font=(self.font_family, max(10, self.font_size - 2))
            ).pack(anchor="w", padx=15, pady=(0, 8))
            return

        editor_bg, editor_fg, _token_bg, _token_fg = self._filename_editor_colors()
        row_states = []

        for note in notes:
            note_id = str(note.get("id") or secrets.token_hex(4))
            note["id"] = note_id

            card = ctk.CTkFrame(parent, fg_color="transparent")
            card.pack(fill="x", padx=15, pady=(0, 8))

            controls = ctk.CTkFrame(card, fg_color="transparent")
            controls.pack(fill="x", pady=(0, 4))

            position = note.get("before_field", "__end__")
            position_var = ctk.StringVar(
                value=position_to_label.get(position, "End of each part")
            )
            ctk.CTkOptionMenu(
                controls,
                values=position_labels,
                variable=position_var,
                width=225
            ).pack(side="left")

            ctk.CTkButton(
                controls,
                text="Delete",
                width=75,
                fg_color="#cc4b4b",
                hover_color="#aa2b2b",
                command=lambda nid=note_id: self.delete_workspace_note(workspace_name, nid)
            ).pack(side="right")

            text_box = tk.Text(
                card,
                height=3,
                wrap="word",
                bg=editor_bg,
                fg=editor_fg,
                insertbackground=editor_fg,
                relief="solid",
                borderwidth=1,
                padx=7,
                pady=6,
                font=(self.font_family, self.font_size)
            )
            text_box.pack(fill="x")
            text_box.insert("1.0", note.get("text", ""))
            row_states.append((note_id, position_var, text_box))

        def save_notes():
            saved_notes = []
            for note_id, position_var, text_box in row_states:
                text = text_box.get("1.0", "end-1c").strip()
                if not text:
                    continue
                saved_notes.append({
                    "id": note_id,
                    "text": text,
                    "before_field": label_to_position.get(position_var.get(), "__end__")
                })

            definition["notes"] = saved_notes
            self.rebuild_runtime_workspaces()
            self.save_settings()
            self.refresh_open_sessions_for_workspace_fields(workspace_name)
            debug(f"Saved {len(saved_notes)} workspace note(s) for {workspace_name}", "saved")
            messagebox.showinfo("Workspace Notes Saved", f"Saved notes for the {workspace_name} workspace.")

        ctk.CTkButton(
            parent,
            text="Save Workspace Notes",
            width=165,
            command=save_notes
        ).pack(anchor="w", padx=15, pady=(0, 10))

    def add_workspace_note(self, workspace_name):
        definition = self.settings.get("workspaces", {}).get(workspace_name)
        if not definition:
            return
        definition.setdefault("notes", []).append({
            "id": secrets.token_hex(4),
            "text": "Reminder",
            "before_field": "__end__"
        })
        self.rebuild_runtime_workspaces()
        self.save_settings()
        self.refresh_workspace_settings_editor(workspace_name)

    def delete_workspace_note(self, workspace_name, note_id):
        definition = self.settings.get("workspaces", {}).get(workspace_name)
        if not definition:
            return
        definition["notes"] = [
            note for note in definition.get("notes", [])
            if str(note.get("id")) != str(note_id)
        ]
        self.rebuild_runtime_workspaces()
        self.save_settings()
        self.refresh_workspace_settings_editor(workspace_name)
        self.refresh_open_sessions_for_workspace_fields(workspace_name)

    def reset_workspace_layout(self, workspace_name):
        definition = self.settings.get("workspaces", {}).get(workspace_name)
        if not definition:
            return
        definition["custom_layout"] = None
        self.rebuild_runtime_workspaces()
        self.save_settings()
        self.refresh_open_sessions_for_workspace_fields(workspace_name)
        self.refresh_workspace_settings_editor(workspace_name)

    def open_workspace_layout_designer(self, workspace_name):
        """Freeform workspace designer with optional square-grid snapping."""
        if workspace_name not in self.settings.get("workspaces", {}):
            return

        definition = self.settings["workspaces"][workspace_name]
        profile = self.get_workspace_profile(workspace_name)
        fields = [field for field in profile.get("fields", []) if field.get("key")]

        win = tk.Toplevel(self)
        window_bg = "#1e1e1e" if ctk.get_appearance_mode() == "Dark" else "#f4f4f4"
        canvas_bg = "#202020" if ctk.get_appearance_mode() == "Dark" else "#f8f8f8"
        grid_color = "#383838" if ctk.get_appearance_mode() == "Dark" else "#dedede"
        win.configure(bg=window_bg)
        win.title(f"{workspace_name} Layout Designer")
        win.geometry("1120x800")
        win.minsize(920, 680)
        win.transient(self)
        win.grab_set()

        ctk.CTkLabel(
            win,
            text=f"{workspace_name} Workspace Designer",
            font=(self.font_family, self.font_size + 5, "bold")
        ).pack(pady=(14, 2))
        ctk.CTkLabel(
            win,
            text=(
                "Drag field tiles anywhere and resize from an edge or corner. The square grid is only a guide "
                "unless Snap to Grid is checked. The PDF viewer stays fixed in Split & Rename."
            ),
            text_color="#888888",
            wraplength=940,
            justify="center",
            font=(self.font_family, max(10, self.font_size - 1))
        ).pack(padx=20, pady=(0, 8))

        toolbar = ctk.CTkFrame(win, fg_color="transparent")
        toolbar.pack(fill="x", padx=18, pady=(0, 5))
        # Snap is ON by default. Keep the preference separate from the layout
        # itself so closing/cancelling the designer still remembers the user's
        # most recent choice without activating a custom layout.
        current = definition.get("custom_layout") if isinstance(definition.get("custom_layout"), dict) else {}
        saved_snap = definition.get(
            "layout_snap_to_grid",
            current.get("snap_to_grid", True) if isinstance(current, dict) else True
        )
        snap_var = ctk.BooleanVar(value=bool(saved_snap))

        def remember_snap_preference():
            definition["layout_snap_to_grid"] = bool(snap_var.get())
            if isinstance(definition.get("custom_layout"), dict):
                definition["custom_layout"]["snap_to_grid"] = bool(snap_var.get())
            self.save_settings()

        ctk.CTkCheckBox(
            toolbar,
            text="Snap to Grid",
            variable=snap_var,
            command=remember_snap_preference
        ).pack(side="left")
        ctk.CTkLabel(
            toolbar,
            text="Drag field tiles and grab their border/corner to resize. The PDF viewer is not part of the tile layout.",
            text_color="#888888",
            font=(self.font_family, max(10, self.font_size - 2))
        ).pack(side="left", padx=(18, 0))

        canvas = tk.Canvas(win, bg=canvas_bg, highlightthickness=1, highlightbackground="#777777")
        canvas.pack(fill="both", expand=True, padx=18, pady=(0, 8))
        win.update_idletasks()

        # `current` is initialized above with the snap preference so the
        # checkbox can remember its state even when the designer is cancelled.
        grid_size = max(12, min(48, int(current.get("grid_size", 24) or 24)))
        raw_elements = copy.deepcopy(current.get("elements", {})) if isinstance(current.get("elements"), dict) else {}
        saved_surface = current.get("surface", {}) if isinstance(current.get("surface"), dict) else {}
        saved_w = max(640, int(saved_surface.get("width", 920) or 920))
        saved_h = max(420, int(saved_surface.get("height", 620) or 620))

        state = {
            "items": {},
            "drag": None,
            "selected": None,
            "mode": None,
            "start_x": 0,
            "start_y": 0,
            "start_box": None,
            "elements": {},
            "surface_w": saved_w,
            "surface_h": saved_h,
        }

        def clamp(value, low, high):
            return max(low, min(high, value))

        def snap(value):
            if not snap_var.get():
                return int(round(value))
            return int(round(value / grid_size) * grid_size)

        def canvas_size():
            return max(640, canvas.winfo_width()), max(420, canvas.winfo_height())

        def scale_saved_box(box, field=None):
            cw, ch = canvas_size()
            sx = cw / max(1, state["surface_w"])
            sy = ch / max(1, state["surface_h"])
            minimum_height = self.get_freeform_tile_min_height(field)
            return {
                "x": int(box.get("x", 0) * sx),
                "y": int(box.get("y", 0) * sy),
                "width": int(box.get("width", 240) * sx),
                "height": max(minimum_height, int(box.get("height", 70) * sy)),
            }

        def default_elements():
            cw, ch = canvas_size()
            result = {}
            x = 34
            y = 40
            width = max(290, int(cw * 0.72))
            for field in fields:
                key = field["key"]
                tile_height = self.get_freeform_tile_min_height(field)
                result[key] = {"x": x, "y": y, "width": width, "height": tile_height}
                y += tile_height + 14
            return result

        # Load v2 freeform rectangles. If there is no custom layout yet, generate
        # a visual version of the normal stacked layout without activating it.
        if raw_elements:
            for key, box in raw_elements.items():
                field = next((item for item in fields if item.get("key") == key), None)
                if field is not None and isinstance(box, dict):
                    state["elements"][key] = scale_saved_box(box, field)
        if not state["elements"]:
            state["elements"] = default_elements()
        else:
            defaults = default_elements()
            for field in fields:
                state["elements"].setdefault(field["key"], defaults[field["key"]])

        handle_size = 8
        resize_cursors = {
            "nw": "top_left_corner", "n": "sb_v_double_arrow", "ne": "top_right_corner",
            "e": "sb_h_double_arrow", "se": "bottom_right_corner", "s": "sb_v_double_arrow",
            "sw": "bottom_left_corner", "w": "sb_h_double_arrow"
        }

        def draw_grid():
            canvas.delete("grid")
            w, h = canvas_size()
            for x in range(0, w + grid_size, grid_size):
                canvas.create_line(x, 0, x, h, fill=grid_color, width=1, tags="grid")
            for y in range(0, h + grid_size, grid_size):
                canvas.create_line(0, y, w, y, fill=grid_color, width=1, tags="grid")
            canvas.tag_lower("grid")

        def item_fill(item_id):
            if item_id == "__preview__":
                return "#8255a5"
            field = next((f for f in fields if f.get("key") == item_id), {})
            return self.get_field_color(field) or "#3B8ED0"

        def label_for(item_id):
            if item_id == "__preview__":
                return "PDF Preview"
            field = next((f for f in fields if f.get("key") == item_id), {})
            return field.get("label", item_id)

        def handle_boxes(box):
            x, y, w, h = box["x"], box["y"], box["width"], box["height"]
            pts = {
                "nw": (x, y), "n": (x + w/2, y), "ne": (x + w, y),
                "e": (x + w, y + h/2), "se": (x + w, y + h),
                "s": (x + w/2, y + h), "sw": (x, y + h), "w": (x, y + h/2)
            }
            out = {}
            for name, (cx, cy) in pts.items():
                out[name] = (cx-handle_size, cy-handle_size, cx+handle_size, cy+handle_size)
            return out

        def redraw():
            canvas.delete("all")
            state["items"].clear()
            draw_grid()
            for item_id, box in state["elements"].items():
                fill = item_fill(item_id)
                outline = "#ffffff" if state.get("selected") == item_id else "#a8a8a8"
                rect = canvas.create_rectangle(
                    box["x"], box["y"], box["x"] + box["width"], box["y"] + box["height"],
                    fill=fill, outline=outline, width=2,
                    tags=("element", f"item:{item_id}")
                )
                text = canvas.create_text(
                    box["x"] + box["width"] / 2,
                    box["y"] + box["height"] / 2,
                    text=label_for(item_id), fill="white",
                    font=(self.font_family, max(10, self.font_size - 1), "bold"),
                    width=max(60, box["width"] - 18),
                    tags=("element", f"item:{item_id}")
                )
                state["items"][item_id] = {"rect": rect, "text": text}

                if state.get("selected") == item_id:
                    for handle, hb in handle_boxes(box).items():
                        canvas.create_rectangle(
                            *hb, fill="#ffffff", outline="#333333", width=1,
                            tags=("resize_handle", f"item:{item_id}", f"handle:{handle}")
                        )
            canvas.tag_lower("grid")

        def parse_tags(canvas_id):
            tags = canvas.gettags(canvas_id)
            item_id = next((t.split(":",1)[1] for t in tags if t.startswith("item:")), None)
            handle = next((t.split(":",1)[1] for t in tags if t.startswith("handle:")), None)
            return item_id, handle

        def press(event):
            found = canvas.find_overlapping(event.x, event.y, event.x, event.y)
            if not found:
                state["selected"] = None
                redraw()
                return
            target = found[-1]
            item_id, handle = parse_tags(target)
            if not item_id:
                return
            state["selected"] = item_id
            state["drag"] = item_id
            state["mode"] = handle or "move"
            state["start_x"] = event.x
            state["start_y"] = event.y
            state["start_box"] = dict(state["elements"][item_id])
            redraw()

        def motion(event):
            item_id = state.get("drag")
            if not item_id:
                return
            box = dict(state["start_box"])
            dx = event.x - state["start_x"]
            dy = event.y - state["start_y"]
            mode = state.get("mode") or "move"
            min_w = 180 if item_id == "__preview__" else 120
            selected_field = next((item for item in fields if item.get("key") == item_id), None)
            min_h = 140 if item_id == "__preview__" else self.get_freeform_tile_min_height(selected_field)
            cw, ch = canvas_size()

            if mode == "move":
                nx = snap(box["x"] + dx)
                ny = snap(box["y"] + dy)
                box["x"] = clamp(nx, 0, max(0, cw - box["width"]))
                box["y"] = clamp(ny, 0, max(0, ch - box["height"]))
            else:
                left = box["x"]
                top = box["y"]
                right = box["x"] + box["width"]
                bottom = box["y"] + box["height"]

                if "w" in mode:
                    left = snap(box["x"] + dx)
                    left = clamp(left, 0, right - min_w)
                if "e" in mode:
                    right = snap(box["x"] + box["width"] + dx)
                    right = clamp(right, left + min_w, cw)
                if "n" in mode:
                    top = snap(box["y"] + dy)
                    top = clamp(top, 0, bottom - min_h)
                if "s" in mode:
                    bottom = snap(box["y"] + box["height"] + dy)
                    bottom = clamp(bottom, top + min_h, ch)

                box["x"] = left
                box["y"] = top
                box["width"] = right - left
                box["height"] = bottom - top

            state["elements"][item_id] = box
            redraw()

        def release(_event):
            state["drag"] = None
            state["mode"] = None
            state["start_box"] = None

        def on_motion_cursor(event):
            found = canvas.find_overlapping(event.x, event.y, event.x, event.y)
            cursor = ""
            if found:
                item_id, handle = parse_tags(found[-1])
                if handle:
                    cursor = resize_cursors.get(handle, "crosshair")
                elif item_id:
                    cursor = "fleur"
            try:
                canvas.configure(cursor=cursor)
            except tk.TclError:
                pass

        def on_configure(_event=None):
            # Keep existing positions stable while resizing the designer window.
            redraw()

        canvas.bind("<ButtonPress-1>", press)
        canvas.bind("<B1-Motion>", motion)
        canvas.bind("<ButtonRelease-1>", release)
        canvas.bind("<Motion>", on_motion_cursor)
        canvas.bind("<Configure>", on_configure)

        footer = ctk.CTkFrame(win, fg_color="transparent")
        footer.pack(fill="x", padx=18, pady=(0, 14))

        def save_layout():
            # Save the field rectangles themselves, but make the logical surface
            # describe the USED tile area instead of the entire designer window.
            # This makes the designer WYSIWYG even when the window is maximized or
            # contains lots of unused grid below/right of the fields.
            elements = {}
            for item_id, box in state["elements"].items():
                elements[item_id] = {
                    "x": int(round(box["x"])),
                    "y": int(round(box["y"])),
                    "width": int(round(box["width"])),
                    "height": int(round(box["height"]))
                }

            used = list(elements.values())
            if used:
                min_x = min(box["x"] for box in used)
                min_y = min(box["y"] for box in used)
                max_right = max(box["x"] + box["width"] for box in used)
                max_bottom = max(box["y"] + box["height"] for box in used)
                pad = 24
                logical_w = max(320, max_right - min_x + pad * 2)
                logical_h = max(120, max_bottom - min_y + pad * 2)
            else:
                logical_w, logical_h = 640, 420

            definition["layout_snap_to_grid"] = bool(snap_var.get())
            definition["custom_layout"] = {
                "enabled": True,
                "version": 4,
                "snap_to_grid": bool(snap_var.get()),
                "grid_size": grid_size,
                "surface": {"width": logical_w, "height": logical_h},
                "elements": elements
            }
            self.rebuild_runtime_workspaces()
            self.save_settings()
            self.refresh_open_sessions_for_workspace_fields(workspace_name)
            self.refresh_workspace_settings_editor(workspace_name)
            win.destroy()

        ctk.CTkLabel(
            footer,
            text="Tip: this designer controls the field tiles only. The PDF viewer remains fixed on the right.",
            text_color="#888888",
            font=(self.font_family, max(10, self.font_size - 2))
        ).pack(side="left")
        ctk.CTkButton(footer, text="Cancel", width=95, command=win.destroy).pack(side="right", padx=(6,0))
        ctk.CTkButton(footer, text="Save Layout", width=120, command=save_layout).pack(side="right")

        win.after(50, redraw)

    def get_workspace_settings(self, workspace_name):
        if workspace_name not in self.settings.get("workspaces", {}):
            workspace_name = "Accounting"
        definition = self.settings["workspaces"][workspace_name]
        desc = definition.get("field_overrides", {}).get("description", {})
        return {
            "default_description": desc.get("default", self.settings.get("custom_fields", {}).get("description", {}).get("default", "")),
            "autofill_description": desc.get("autofill", self.settings.get("custom_fields", {}).get("description", {}).get("autofill", True)),
            "filename_template": definition.get("filename_template", "{client}_{date}")
        }

    def save_workspace_setting(self, workspace_name, key, value):
        if workspace_name not in self.settings.get("workspaces", {}):
            workspace_name = "Accounting"
        definition = self.settings["workspaces"][workspace_name]

        if key == "filename_template":
            definition["filename_template"] = value
        elif key in {"default_description", "autofill_description"}:
            desc = definition.setdefault("field_overrides", {}).setdefault("description", {})
            desc["default" if key == "default_description" else "autofill"] = value
        else:
            definition[key] = value

        legacy = self.settings.setdefault("workspace_settings", {}).setdefault(workspace_name, {})
        if key in {"filename_template", "default_description", "autofill_description"}:
            legacy[key] = value

        if workspace_name == "Accounting":
            if key == "filename_template":
                self.settings["filename_template"] = value
            elif key == "default_description":
                self.settings["default_description"] = value
            elif key == "autofill_description":
                self.settings["autofill_description"] = value

        self.rebuild_runtime_workspaces()
        self.save_settings()
        debug(f"{workspace_name} workspace setting saved: {key}={value!r}", "saved")

    def save_workspace_filename_template(self, workspace_name, variable):
        value = variable.get().strip()
        if not value:
            value = self.settings["workspaces"][workspace_name].get("filename_template", "{client}_{date}")
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
            field_color = self.get_field_color(token)
            if field_color:
                token_bg = field_color
                token_fg = self.contrast_text_for_hex(field_color, token_fg)

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
            "description": "Invoice",
            "agency_description": "IRS Invoice",
            "date": "8-20-2026",
            "matter_number": "24-0152",
            "document_type": "Notice"
        }
        profile = self.get_workspace_profile(workspace_name)
        for field in profile.get("fields", []):
            key = field.get("key")
            if not key or key in values:
                continue
            field_type = field.get("type", "text")
            if field_type == "currency":
                sample = "$134.06"
            elif field_type == "date":
                try:
                    sample = self.format_date_for_field("8-20-2026", field)
                except Exception:
                    sample = "8-20-2026"
            elif field_type == "number":
                sample = "123"
            elif field_type in {"checkbox", "toggle", "bool"}:
                sample = field.get("label", "Yes")
            elif field_type == "choice":
                options = [str(x) for x in field.get("options", [])]
                sample = next((x for x in options if x.casefold() != "other"), "Sample")
            else:
                sample = "Sample"
            values[key] = sample
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

    def _build_custom_fields_section(self, parent):
        scroll = ctk.CTkScrollableFrame(parent)
        scroll.pack(fill="both", expand=True, padx=8, pady=8)
        self.custom_fields_scroll = scroll

        bubble_color, border_color = self.get_log_bubble_colors()

        library = ctk.CTkFrame(
            scroll, fg_color=bubble_color, border_color=border_color,
            border_width=2, corner_radius=10
        )
        library.pack(fill="x", padx=4, pady=(4, 10))

        ctk.CTkLabel(
            library, text="🧩 Custom Field Library",
            font=(self.font_family, self.font_size + 2, "bold")
        ).pack(anchor="w", padx=15, pady=(12, 4))
        ctk.CTkLabel(
            library,
            text=(
                "Fields are reusable across workspaces. Select a field to edit all of its settings, "
                "or create a new one. Built-in fields can be edited but not deleted."
            ),
            text_color="#888888", wraplength=720, justify="left",
            font=(self.font_family, max(10, self.font_size - 1))
        ).pack(anchor="w", padx=15, pady=(0, 8))

        row = ctk.CTkFrame(library, fg_color="transparent")
        row.pack(fill="x", padx=15, pady=(0, 12))
        self.custom_field_selector_var = ctk.StringVar()
        self.custom_field_selector = ctk.CTkOptionMenu(
            row, values=["Loading..."], variable=self.custom_field_selector_var,
            command=self.show_custom_field_editor, width=260
        )
        self.custom_field_selector.pack(side="left", padx=(0, 8))
        ctk.CTkButton(row, text="+ New Field", width=105, command=self.create_custom_field).pack(side="left", padx=4)
        ctk.CTkButton(
            row, text="Delete Field", width=105,
            fg_color="#cc4b4b", hover_color="#aa2b2b",
            command=self.delete_selected_custom_field
        ).pack(side="left", padx=4)

        self.custom_field_editor = ctk.CTkFrame(scroll, fg_color="transparent")
        self.custom_field_editor.pack(fill="x", padx=4, pady=(0, 10))

        assignment = ctk.CTkFrame(
            scroll, fg_color=bubble_color, border_color=border_color,
            border_width=2, corner_radius=10
        )
        assignment.pack(fill="both", expand=True, padx=4, pady=(0, 12))
        self.custom_field_assignment_frame = assignment

        ctk.CTkLabel(
            assignment, text="🗂 Workspace Field Assignment",
            font=(self.font_family, self.font_size + 2, "bold")
        ).pack(anchor="w", padx=15, pady=(12, 4))
        ctk.CTkLabel(
            assignment,
            text="Assign reusable fields here. Drag items in the Assigned list to change their order in the form.",
            text_color="#888888", wraplength=720, justify="left",
            font=(self.font_family, max(10, self.font_size - 1))
        ).pack(anchor="w", padx=15, pady=(0, 8))

        workspace_row = ctk.CTkFrame(assignment, fg_color="transparent")
        workspace_row.pack(fill="x", padx=15, pady=(0, 8))
        ctk.CTkLabel(workspace_row, text="Workspace:").pack(side="left", padx=(0, 8))
        self.custom_assignment_workspace_var = ctk.StringVar(
            value=self.settings.get("default_workspace", "Accounting")
        )
        self.custom_assignment_workspace_menu = ctk.CTkOptionMenu(
            workspace_row, values=list(WORKSPACES.keys()),
            variable=self.custom_assignment_workspace_var,
            command=lambda _value: self.refresh_workspace_field_assignment(),
            width=190
        )
        self.custom_assignment_workspace_menu.pack(side="left")

        lists = ctk.CTkFrame(assignment, fg_color="transparent")
        lists.pack(fill="both", expand=True, padx=15, pady=(0, 12))

        left = ctk.CTkFrame(lists, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(left, text="Available Fields", font=(self.font_family, self.font_size, "bold")).pack()
        list_bg, list_fg, list_select_bg, list_select_fg = self._filename_editor_colors()
        self.available_fields_list = tk.Listbox(
            left,
            height=9,
            exportselection=False,
            font=(self.font_family, max(10, self.font_size - 1)),
            bg=list_bg,
            fg=list_fg,
            selectbackground=list_select_bg,
            selectforeground=list_select_fg,
            activestyle="none",
            relief="solid",
            borderwidth=1,
            highlightthickness=0
        )
        self.available_fields_list.pack(fill="both", expand=True, pady=(4, 0))

        middle = ctk.CTkFrame(lists, fg_color="transparent", width=96)
        middle.pack(side="left", fill="y", padx=6)
        middle.pack_propagate(False)
        assignment_button_font = (self.font_family, 11)
        ctk.CTkButton(
            middle,
            text="Add →",
            width=88,
            height=28,
            font=assignment_button_font,
            command=self.assign_selected_field
        ).pack(pady=(38, 7))
        ctk.CTkButton(
            middle,
            text="← Remove",
            width=88,
            height=28,
            font=assignment_button_font,
            command=self.unassign_selected_field
        ).pack(pady=7)

        right = ctk.CTkFrame(lists, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(right, text="Assigned (drag to reorder)", font=(self.font_family, self.font_size, "bold")).pack()
        self.assigned_fields_list = tk.Listbox(
            right,
            height=9,
            exportselection=False,
            font=(self.font_family, max(10, self.font_size - 1)),
            bg=list_bg,
            fg=list_fg,
            selectbackground=list_select_bg,
            selectforeground=list_select_fg,
            activestyle="none",
            relief="solid",
            borderwidth=1,
            highlightthickness=0
        )
        self.assigned_fields_list.pack(fill="both", expand=True, pady=(4, 0))
        self.assigned_fields_list.bind("<Button-1>", self._assignment_drag_start)
        self.assigned_fields_list.bind("<B1-Motion>", self._assignment_drag_motion)
        self.assigned_fields_list.bind("<ButtonRelease-1>", self._assignment_drag_end)
        self.assigned_fields_list.bind("<Double-Button-1>", lambda _event: self.unassign_selected_field())
        self._assignment_drag_index = None
        self._assignment_drag_moved = False

        self.refresh_custom_field_selector()
        self.refresh_workspace_field_assignment()

    def _field_display_name(self, key):
        field = self.settings.get("custom_fields", {}).get(key, {})
        return f"{field.get('label', key)}  [{key}]"

    def refresh_custom_field_selector(self, select_key=None):
        fields = self.settings.get("custom_fields", {})
        self.custom_field_display_to_key = {
            self._field_display_name(key): key for key in fields
        }
        values = list(self.custom_field_display_to_key.keys()) or ["No fields"]
        self.custom_field_selector.configure(values=values)

        if select_key not in fields:
            current = self.custom_field_display_to_key.get(self.custom_field_selector_var.get())
            select_key = current if current in fields else (next(iter(fields), None))
        if select_key:
            display = self._field_display_name(select_key)
            self.custom_field_selector_var.set(display)
            self.show_custom_field_editor(display)

    def create_custom_field(self):
        label = simpledialog.askstring("New Custom Field", "Field name:", parent=self)
        if not label:
            return
        label = label.strip()
        if not label:
            return

        base_key = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_") or "field"
        key = base_key
        counter = 2
        fields = self.settings.setdefault("custom_fields", {})
        while key in fields:
            key = f"{base_key}_{counter}"
            counter += 1

        fields[key] = {
            "key": key,
            "label": label,
            "type": "text",
            "placeholder": "",
            "default": "",
            "required": False,
            "autofill": True,
            "title_case": False,
            "date_format": "M-D-YYYY",
            "options": ["Other"],
            "condition": None,
            "placement": "standard",
            "color": "",
            "system": False
        }
        self.save_settings()
        self.rebuild_runtime_workspaces()
        self.refresh_custom_field_selector(key)
        self.refresh_workspace_field_assignment()

    def delete_selected_custom_field(self):
        key = self.custom_field_display_to_key.get(self.custom_field_selector_var.get())
        if not key:
            return
        field = self.settings.get("custom_fields", {}).get(key, {})
        if field.get("system"):
            messagebox.showinfo("Built-in Field", "Built-in fields can be edited or unassigned, but not deleted.")
            return
        if not messagebox.askyesno("Delete Field", f"Delete the '{field.get('label', key)}' field?"):
            return

        self.settings["custom_fields"].pop(key, None)
        for definition in self.settings.get("workspaces", {}).values():
            definition["field_keys"] = [item for item in definition.get("field_keys", []) if item != key]
            definition.get("field_overrides", {}).pop(key, None)
            layout = definition.get("custom_layout")
            if isinstance(layout, dict):
                layout.get("elements", {}).pop(key, None)
                layout.get("field_positions", {}).pop(key, None)

        for other in self.settings.get("custom_fields", {}).values():
            condition = other.get("condition")
            if isinstance(condition, dict) and condition.get("field") == key:
                other["condition"] = None

        self.rebuild_runtime_workspaces()
        self.save_settings()
        self.refresh_custom_field_selector()
        self.refresh_workspace_field_assignment()
        self.refresh_open_sessions_for_workspace_fields()

    def normalize_field_color(self, value):
        raw = str(value or "").strip()
        if not raw:
            return ""
        if re.fullmatch(r"[0-9A-Fa-f]{6}", raw):
            raw = "#" + raw
        if re.fullmatch(r"#[0-9A-Fa-f]{3}", raw):
            raw = "#" + "".join(char * 2 for char in raw[1:])
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", raw):
            raise ValueError("Field color must be a hex color such as #3B8ED0.")
        return raw.upper()

    def get_field_color(self, field_or_key):
        if isinstance(field_or_key, dict):
            raw = field_or_key.get("color", "")
        else:
            raw = self.settings.get("custom_fields", {}).get(str(field_or_key), {}).get("color", "")
        try:
            return self.normalize_field_color(raw)
        except ValueError:
            return ""

    def contrast_text_for_hex(self, color, fallback="#FFFFFF"):
        try:
            normalized = self.normalize_field_color(color)
            if not normalized:
                return fallback
            red = int(normalized[1:3], 16)
            green = int(normalized[3:5], 16)
            blue = int(normalized[5:7], 16)
            luminance = (0.299 * red) + (0.587 * green) + (0.114 * blue)
            return "#000000" if luminance > 165 else "#FFFFFF"
        except Exception:
            return fallback

    def show_custom_field_editor(self, display_or_key):
        key = self.custom_field_display_to_key.get(display_or_key, display_or_key)
        fields = self.settings.get("custom_fields", {})
        if key not in fields:
            return
        field = fields[key]

        for child in self.custom_field_editor.winfo_children():
            child.destroy()

        bubble_color, border_color = self.get_log_bubble_colors()
        bubble = ctk.CTkFrame(
            self.custom_field_editor, fg_color=bubble_color,
            border_color=border_color, border_width=2, corner_radius=10
        )
        bubble.pack(fill="x")

        title = field.get("label", key)
        system_text = " (Built-in)" if field.get("system") else ""
        ctk.CTkLabel(
            bubble, text=f"{title}{system_text}",
            font=(self.font_family, self.font_size + 2, "bold")
        ).pack(anchor="w", padx=15, pady=(12, 8))

        grid = ctk.CTkFrame(bubble, fg_color="transparent")
        grid.pack(fill="x", padx=15)
        grid.grid_columnconfigure(1, weight=1)

        label_var = ctk.StringVar(value=field.get("label", key))
        type_reverse = {label: value for value, label in CUSTOM_FIELD_TYPE_LABELS.items()}
        type_var = ctk.StringVar(value=CUSTOM_FIELD_TYPE_LABELS.get(field.get("type", "text"), "Text"))
        placeholder_var = ctk.StringVar(value=field.get("placeholder", ""))
        default_value = field.get("default", "")
        if isinstance(default_value, bool):
            default_value = "True" if default_value else "False"
        default_var = ctk.StringVar(value=str(default_value))
        required_var = ctk.BooleanVar(value=bool(field.get("required", False)))
        autofill_var = ctk.BooleanVar(value=bool(field.get("autofill", True)))
        title_case_var = ctk.BooleanVar(value=bool(field.get("title_case", False)))
        date_format_var = ctk.StringVar(value=field.get("date_format", "M-D-YYYY"))
        auto_today_var = ctk.BooleanVar(value=bool(field.get("auto_today", False)))
        color_var = ctk.StringVar(value=field.get("color", ""))
        condition_enabled_var = ctk.BooleanVar(value=isinstance(field.get("condition"), dict))

        row_index = 0
        def add_label(text):
            nonlocal row_index
            ctk.CTkLabel(grid, text=text).grid(row=row_index, column=0, sticky="w", padx=(0, 10), pady=4)

        add_label("Field label")
        CTkEntry(grid, textvariable=label_var).grid(row=row_index, column=1, sticky="ew", pady=4)
        row_index += 1

        add_label("Data type")
        type_menu = ctk.CTkOptionMenu(
            grid,
            values=list(CUSTOM_FIELD_TYPE_LABELS.values()),
            variable=type_var
        )
        type_menu.grid(row=row_index, column=1, sticky="ew", pady=4)
        row_index += 1

        add_label("Placeholder")
        CTkEntry(grid, textvariable=placeholder_var).grid(row=row_index, column=1, sticky="ew", pady=4)
        row_index += 1

        add_label("Default value")
        CTkEntry(grid, textvariable=default_var).grid(row=row_index, column=1, sticky="ew", pady=4)
        row_index += 1

        add_label("Field color (hex)")
        color_row = ctk.CTkFrame(grid, fg_color="transparent")
        color_row.grid(row=row_index, column=1, sticky="ew", pady=4)
        color_row.grid_columnconfigure(0, weight=1)
        color_entry = CTkEntry(color_row, textvariable=color_var, placeholder_text="#3B8ED0")
        color_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        color_swatch = ctk.CTkLabel(color_row, text="■", width=28, font=(self.font_family, self.font_size + 6))
        color_swatch.grid(row=0, column=1, padx=(0, 6))

        def refresh_color_swatch(*_args):
            try:
                swatch_color = self.normalize_field_color(color_var.get()) or "#888888"
            except ValueError:
                swatch_color = "#888888"
            color_swatch.configure(text_color=swatch_color)

        def choose_field_color():
            initial = self.get_field_color({"color": color_var.get()}) or "#3B8ED0"
            chosen = colorchooser.askcolor(color=initial, parent=self)[1]
            if chosen:
                color_var.set(chosen.upper())

        ctk.CTkButton(color_row, text="Pick...", width=70, command=choose_field_color).grid(row=0, column=2, padx=(0, 4))
        ctk.CTkButton(color_row, text="Clear", width=60, command=lambda: color_var.set("")).grid(row=0, column=3)
        color_var.trace_add("write", refresh_color_swatch)
        refresh_color_swatch()
        row_index += 1

        toggles = ctk.CTkFrame(bubble, fg_color="transparent")
        toggles.pack(fill="x", padx=15, pady=(8, 6))
        ctk.CTkCheckBox(toggles, text="Required", variable=required_var).pack(side="left", padx=(0, 16))
        ctk.CTkCheckBox(toggles, text="Autofill to following parts", variable=autofill_var).pack(side="left", padx=(0, 16))
        ctk.CTkCheckBox(toggles, text="Smart title case", variable=title_case_var).pack(side="left")

        # Only show settings that apply to the selected field type.
        # This keeps, for example, Currency fields from displaying Date or
        # Dropdown-specific controls that cannot affect them.
        type_specific = ctk.CTkFrame(bubble, fg_color="transparent")
        type_specific.pack(fill="x")

        date_row = ctk.CTkFrame(type_specific, fg_color="transparent")
        ctk.CTkLabel(date_row, text="Date output format:").pack(side="left", padx=(0, 8))
        ctk.CTkOptionMenu(date_row, values=DATE_FORMATS, variable=date_format_var, width=180).pack(side="left")
        ctk.CTkLabel(
            date_row, text="(Today button follows this format)",
            text_color="#888888", font=(self.font_family, max(10, self.font_size - 2))
        ).pack(side="left", padx=8)
        ctk.CTkCheckBox(
            date_row, text="Autofill this field with today's date", variable=auto_today_var
        ).pack(side="left", padx=8)

        choices_section = ctk.CTkFrame(type_specific, fg_color="transparent")
        ctk.CTkLabel(
            choices_section, text="Dropdown choices (one per line)",
            font=(self.font_family, self.font_size)
        ).pack(anchor="w", pady=(4, 2))
        # Use a standard Tk Text widget here instead of CTkTextbox.
        # Existing CleanCutPDF custom theme JSON files (especially the Pink themes)
        # may predate CTkTextbox and therefore do not contain a CTkTextbox theme key.
        editor_bg, editor_fg, _token_bg, _token_fg = self._filename_editor_colors()
        choices_box = tk.Text(
            choices_section,
            height=4,
            wrap="none",
            bg=editor_bg,
            fg=editor_fg,
            insertbackground=editor_fg,
            selectbackground=_token_bg,
            selectforeground=_token_fg,
            relief="solid",
            borderwidth=1,
            highlightthickness=0,
            padx=6,
            pady=5,
            font=(self.font_family, self.font_size)
        )
        choices_box.pack(fill="x", pady=(0, 8))
        choices_box.insert("1.0", "\n".join(field.get("options", [])))
        ctk.CTkLabel(
            choices_section,
            text="If a choice named Other is present, selecting it shows a free-text box.",
            text_color="#888888", font=(self.font_family, max(10, self.font_size - 2))
        ).pack(anchor="w", pady=(0, 8))

        def update_type_specific_settings(selected_label=None):
            selected_label = selected_label or type_var.get()
            selected_type = type_reverse.get(selected_label, "text")

            date_row.pack_forget()
            choices_section.pack_forget()

            if selected_type == "date":
                date_row.pack(fill="x", padx=15, pady=(4, 8))
            elif selected_type == "choice":
                choices_section.pack(fill="x", padx=15, pady=(4, 0))

        type_menu.configure(command=update_type_specific_settings)
        update_type_specific_settings(type_var.get())

        condition = field.get("condition") if isinstance(field.get("condition"), dict) else {}
        condition_box = ctk.CTkFrame(bubble, fg_color="transparent")
        condition_box.pack(fill="x", padx=15, pady=(4, 8))
        ctk.CTkCheckBox(
            condition_box, text="Conditional visibility", variable=condition_enabled_var
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 6))

        other_fields = [(other_key, self._field_display_name(other_key)) for other_key in fields if other_key != key]
        condition_labels = [label for _key, label in other_fields] or ["No other fields"]
        label_to_key = {label: other_key for other_key, label in other_fields}
        current_condition_key = condition.get("field", "")
        current_condition_label = next((label for other_key, label in other_fields if other_key == current_condition_key), condition_labels[0])
        condition_field_var = ctk.StringVar(value=current_condition_label)
        condition_value_var = ctk.StringVar(value=str(condition.get("equals", "")))

        ctk.CTkLabel(condition_box, text="Show when").grid(row=1, column=0, sticky="w", padx=(0, 6))
        ctk.CTkOptionMenu(condition_box, values=condition_labels, variable=condition_field_var, width=180).grid(
            row=1, column=1, sticky="w", padx=(0, 6)
        )
        ctk.CTkLabel(condition_box, text="equals").grid(row=1, column=2, sticky="w", padx=(0, 6))
        CTkEntry(condition_box, textvariable=condition_value_var, width=180).grid(row=1, column=3, sticky="ew")
        condition_box.grid_columnconfigure(3, weight=1)

        def save_field():
            new_type = type_reverse.get(type_var.get(), "text")
            field["label"] = label_var.get().strip() or key.replace("_", " ").title()
            field["type"] = new_type
            field["placeholder"] = placeholder_var.get()
            field["required"] = bool(required_var.get())
            field["autofill"] = bool(autofill_var.get())
            field["title_case"] = bool(title_case_var.get())
            field["date_format"] = date_format_var.get() if date_format_var.get() in DATE_FORMATS else "M-D-YYYY"
            field["auto_today"] = bool(auto_today_var.get()) if new_type == "date" else False
            try:
                field["color"] = self.normalize_field_color(color_var.get())
            except ValueError as error:
                messagebox.showerror("Invalid Field Color", str(error))
                return

            raw_default = default_var.get().strip()
            if new_type in {"checkbox", "toggle"}:
                field["default"] = raw_default.lower() in {"1", "true", "yes", "on", "checked"}
            else:
                field["default"] = raw_default

            options = [line.strip() for line in choices_box.get("1.0", "end").splitlines() if line.strip()]
            field["options"] = options

            if condition_enabled_var.get() and other_fields:
                controller = label_to_key.get(condition_field_var.get())
                if controller:
                    field["condition"] = {
                        "field": controller,
                        "equals": condition_value_var.get().strip()
                    }
                else:
                    field["condition"] = None
            else:
                field["condition"] = None

            self.rebuild_runtime_workspaces()
            self.save_settings()
            self.refresh_custom_field_selector(key)
            self.refresh_workspace_field_assignment()
            self.refresh_open_sessions_for_workspace_fields()

            # The filename editor builds its Insert Field list when the workspace
            # settings panel is rendered. If an assigned custom field is renamed
            # or otherwise edited, rebuild the currently selected workspace editor
            # so its filename token menu immediately reflects the field library.
            if (
                hasattr(self, "workspace_settings_selector_var")
                and hasattr(self, "workspace_settings_editor")
            ):
                selected_workspace = self.workspace_settings_selector_var.get()
                if selected_workspace in self.settings.get("workspaces", {}):
                    self.refresh_workspace_settings_editor(selected_workspace)

            messagebox.showinfo("Field Saved", f"Settings for '{field['label']}' were saved.")

        ctk.CTkButton(bubble, text="Save Field Settings", command=save_field, width=170).pack(
            anchor="w", padx=15, pady=(4, 14)
        )

    def refresh_workspace_field_assignment(self):
        if not hasattr(self, "available_fields_list"):
            return
        workspace_name = self.custom_assignment_workspace_var.get()
        if workspace_name not in self.settings.get("workspaces", {}):
            workspace_name = "Accounting"
            self.custom_assignment_workspace_var.set(workspace_name)

        fields = self.settings.get("custom_fields", {})
        assigned = list(self.settings["workspaces"][workspace_name].get("field_keys", []))
        assigned = [key for key in assigned if key in fields]
        available = [key for key in fields if key not in assigned]

        self.assignment_assigned_keys = assigned
        self.assignment_available_keys = available

        self.available_fields_list.delete(0, "end")
        for key in available:
            self.available_fields_list.insert("end", self._field_display_name(key))
            color = self.get_field_color(key)
            if color:
                try:
                    self.available_fields_list.itemconfig(self.available_fields_list.size() - 1, foreground=color)
                except tk.TclError:
                    pass

        self.assigned_fields_list.delete(0, "end")
        for key in assigned:
            self.assigned_fields_list.insert("end", self._field_display_name(key))
            color = self.get_field_color(key)
            if color:
                try:
                    self.assigned_fields_list.itemconfig(self.assigned_fields_list.size() - 1, foreground=color)
                except tk.TclError:
                    pass

    def assign_selected_field(self):
        selection = self.available_fields_list.curselection()
        if not selection:
            return
        key = self.assignment_available_keys[selection[0]]
        workspace_name = self.custom_assignment_workspace_var.get()
        definition = self.settings["workspaces"][workspace_name]
        if key not in definition.setdefault("field_keys", []):
            definition["field_keys"].append(key)
        self._save_field_assignment_change(workspace_name)

    def unassign_selected_field(self):
        selection = self.assigned_fields_list.curselection()
        if not selection:
            messagebox.showinfo("Remove Field", "Select a field in the Assigned list first.")
            return
        key = self.assignment_assigned_keys[selection[0]]
        workspace_name = self.custom_assignment_workspace_var.get()
        definition = self.settings["workspaces"][workspace_name]
        definition["field_keys"] = [item for item in definition.get("field_keys", []) if item != key]
        definition.get("field_overrides", {}).pop(key, None)
        layout = definition.get("custom_layout")
        if isinstance(layout, dict):
            layout.get("elements", {}).pop(key, None)
            layout.get("field_positions", {}).pop(key, None)
        for note in definition.get("notes", []):
            if isinstance(note, dict) and note.get("before_field") == key:
                note["before_field"] = "__end__"
        debug(f"Removed field '{key}' from workspace '{workspace_name}'", "saved")
        self._save_field_assignment_change(workspace_name)

    def _assignment_drag_start(self, event):
        if not self.assignment_assigned_keys:
            self._assignment_drag_index = None
            self._assignment_drag_moved = False
            return
        self._assignment_drag_index = self.assigned_fields_list.nearest(event.y)
        self._assignment_drag_moved = False

    def _assignment_drag_motion(self, event):
        if self._assignment_drag_index is None or not self.assignment_assigned_keys:
            return
        new_index = self.assigned_fields_list.nearest(event.y)
        old_index = self._assignment_drag_index
        if new_index == old_index or new_index < 0 or new_index >= len(self.assignment_assigned_keys):
            return

        key = self.assignment_assigned_keys.pop(old_index)
        self.assignment_assigned_keys.insert(new_index, key)
        self._assignment_drag_moved = True
        self.assigned_fields_list.delete(0, "end")
        for item in self.assignment_assigned_keys:
            self.assigned_fields_list.insert("end", self._field_display_name(item))
            color = self.get_field_color(item)
            if color:
                try:
                    self.assigned_fields_list.itemconfig(self.assigned_fields_list.size() - 1, foreground=color)
                except tk.TclError:
                    pass
        self.assigned_fields_list.selection_set(new_index)
        self._assignment_drag_index = new_index

    def _assignment_drag_end(self, _event):
        if self._assignment_drag_index is None:
            return
        moved = bool(getattr(self, "_assignment_drag_moved", False))
        self._assignment_drag_index = None
        self._assignment_drag_moved = False
        # A normal click should only select the row. Earlier builds rebuilt the
        # list on every mouse release, which immediately erased that selection
        # before the user could press Remove.
        if not moved:
            return
        workspace_name = self.custom_assignment_workspace_var.get()
        self.settings["workspaces"][workspace_name]["field_keys"] = list(self.assignment_assigned_keys)
        self._save_field_assignment_change(workspace_name)

    def _save_field_assignment_change(self, workspace_name):
        self.rebuild_runtime_workspaces()
        self.save_settings()
        self.refresh_workspace_field_assignment()
        self.refresh_open_sessions_for_workspace_fields(workspace_name)

        # build_visual_filename_editor() snapshots the available field tokens at
        # render time. Rebuild the workspace editor after assignment/reordering so
        # newly assigned custom fields appear in the filename Insert Field menu
        # immediately instead of requiring a restart or workspace switch.
        if (
            hasattr(self, "workspace_settings_selector_var")
            and hasattr(self, "workspace_settings_editor")
            and self.workspace_settings_selector_var.get() == workspace_name
        ):
            self.refresh_workspace_settings_editor(workspace_name)

        debug(f"Updated field assignment for {workspace_name}", "saved")

    def refresh_open_sessions_for_workspace_fields(self, workspace_name=None):
        for session in list(self.pdf_sessions.values()):
            if workspace_name and session.get("workspace") != workspace_name:
                continue
            if not session.get("is_rendered", False):
                self._render_pdf_placeholder(session)
                continue
            self.capture_workspace_data(session)
            try:
                self.render_splitter_tab(session["tab"], session)
            except tk.TclError:
                pass

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
                if getattr(widget, "_cleancut_note_label", False):
                    widget.configure(font=ctk.CTkFont(
                        family=self.font_family,
                        size=max(10, self.font_size - 1),
                        slant="italic"
                    ))
                else:
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
            self._refresh_pdf_navigation()
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
        field_type = field.get("type", "text")
        if field_type in {"checkbox", "toggle", "bool"}:
            return bool(field.get("default", False))
        return field.get("default", "")

    def get_freeform_tile_min_height(self, field=None):
        """Return the minimum on-screen height needed by a tiled field.

        A tiled field contains a label band and a control band.  Earlier builds
        made the child control taller without guaranteeing that the tile itself
        was tall enough, so the bottom border was clipped and the next tile
        painted over it.  This value is shared by the designer and renderer and
        grows with the user's font size.
        """
        try:
            font_size = max(10, int(self.font_size))
        except Exception:
            font_size = 12

        label_band = max(30, font_size + 12)
        control_band = max(46, font_size + 24)
        padding_and_gap = 16
        minimum = label_band + control_band + padding_and_gap

        field_type = (field or {}).get("type", "text")
        if field_type in {"checkbox", "toggle", "bool"}:
            minimum = max(minimum, 88)

        return max(96, minimum)

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
        self._update_pdf_sidebar_workspace_labels()
        # Rebuild the explorer as well so the visible Inbox row is guaranteed
        # to reflect the manually selected workspace, including after the row
        # has been recreated by a prior selection or folder change.
        self._refresh_pdf_sidebar()

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
    def build_quick_split_filename(self, original_name, part_number):
        original_name = re.sub(r'[\\/*?:"<>|]', "_", str(original_name)).strip(" .") or "Document"
        part_name = f"Part {part_number:02d}"
        order = self.settings.get("quick_split_filename_order", QUICK_SPLIT_FILENAME_ORDERS[0])

        if order == "Part Number - Original Name":
            return f"{part_name} – {original_name}"
        if order == "Original Name Only":
            return original_name
        if order == "Part Number Only":
            return part_name
        return f"{original_name} – {part_name}"

    def get_unique_output_path(self, folder, base_name, extension=".pdf"):
        folder = Path(folder)
        candidate = folder / f"{base_name}{extension}"
        counter = 2
        while candidate.exists():
            candidate = folder / f"{base_name}_{counter}{extension}"
            counter += 1
        return candidate

    def load_quick_split_pdf_from_path(self, path):
        fitz_doc = None
        self.show_loading_overlay(f"Quick splitting…\n{Path(path).name}")
        self.update_idletasks()
        try:
            reader = PdfReader(path)
            ranges = self.detect_split_ranges_from_reader(reader, source_path=path)
            self.warn_if_no_split_markers(reader, path)

            out_folder = Path(self.settings.get("export_folder", "")) or Path.home() / "Desktop"
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            export_dir = out_folder / "Quick Split Files" / today_str
            export_dir.mkdir(parents=True, exist_ok=True)

            remove_blanks = self.settings.get("remove_blank_pages", True)
            if remove_blanks:
                try:
                    fitz_doc = fitz.open(str(path))
                except Exception as error:
                    debug(f"Could not open visual blank-page checker for Quick Split: {error}", "warning")

            skipped_pages = []
            created_files = []
            original_name = Path(path).stem

            for i, r in enumerate(ranges, start=1):
                writer = PdfWriter()
                for p in range(r["start"], r["end"] + 1):
                    page = reader.pages[p]
                    fitz_page = None
                    if fitz_doc is not None and p < fitz_doc.page_count:
                        try:
                            fitz_page = fitz_doc.load_page(p)
                        except Exception:
                            fitz_page = None

                    if remove_blanks and self.is_blank_page(page, fitz_page=fitz_page):
                        skipped_pages.append(p + 1)
                        continue
                    writer.add_page(page)

                base_name = self.build_quick_split_filename(original_name, i)
                file_path = self.get_unique_output_path(export_dir, base_name)
                with open(file_path, "wb") as f:
                    writer.write(f)
                created_files.append(file_path)

            debug(
                f"{len(created_files)} Quick Split file(s) saved to: {export_dir}; "
                f"blank pages removed: {skipped_pages if skipped_pages else 'None'}",
                "saved"
            )
            self.hide_loading_overlay()
            messagebox.showinfo(
                "Quick Split Complete",
                f"{len(created_files)} files saved to:\n{export_dir}" +
                (f"\n\nBlank pages removed: {', '.join(map(str, skipped_pages))}" if skipped_pages else "")
            )

        except Exception as e:
            debug(f"Failed to quick split: \n{e}", "error")
            self.hide_loading_overlay()
            messagebox.showerror("Error", f"Failed to quick split:\n{e}")
        finally:
            if fitz_doc is not None:
                try:
                    fitz_doc.close()
                except Exception:
                    pass

    def parse_dropped_paths(self, raw_data):
        """Parse a TkDND file-list payload without breaking paths that contain spaces."""
        raw = str(raw_data or "").strip()
        if not raw:
            return []
        try:
            return [str(item) for item in self.tk.splitlist(raw)]
        except tk.TclError:
            # Fallback for malformed/older drag payloads.
            braced = re.findall(r"\{(.*?)\}", raw)
            return braced or [raw]

    def handle_quick_drop(self, event):
        paths = self.parse_dropped_paths(event.data)
        valid_pdfs = [p for p in paths if Path(p).suffix.lower() == ".pdf"]

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

    def update_autofill_today_setting(self):
        enabled = bool(self.autofill_today_var.get()) if hasattr(self, "autofill_today_var") else False
        self.settings["autofill_todays_date"] = enabled
        self.save_settings()
        # Refresh open forms so blank Date fields immediately reflect the setting.
        self.refresh_open_sessions_for_workspace_fields()

    def update_quick_split_filename_order(self, selected=None):
        value = selected or (
            self.quick_split_filename_order_var.get()
            if hasattr(self, "quick_split_filename_order_var")
            else QUICK_SPLIT_FILENAME_ORDERS[0]
        )
        if value not in QUICK_SPLIT_FILENAME_ORDERS:
            value = QUICK_SPLIT_FILENAME_ORDERS[0]
        self.settings["quick_split_filename_order"] = value
        self.save_settings()

    def update_no_split_warning_setting(self):
        suppress = not self.no_split_warning_var.get()
        self.settings["suppressNoSplitWarning"] = suppress
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
            self.refresh_folder_shortcut_bar()
            self.save_settings()

            if prev != folder:
                self.append_log_lines([
                    f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Export folder changed from '{prev}' to '{folder}'\n"
                ])

            self.load_full_log()
    def update_retain_client_setting(self):
        self.settings["retain_client_name"] = self.retain_client_var.get()
        self.save_settings()
    def start_auto_save_sessions(self):
        self.auto_save_interval = 30000
        if getattr(self, "pdf_sessions", None):
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
    def append_log_lines(self, lines):
        """Append log entries while keeping the on-disk log bounded."""
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as handle:
                handle.writelines(lines)

            if LOG_FILE.stat().st_size > MAX_LOG_BYTES:
                with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as handle:
                    retained = handle.readlines()[-MAX_LOG_ENTRIES:]
                temporary = LOG_FILE.with_name(f".{LOG_FILE.name}.tmp")
                with open(temporary, "w", encoding="utf-8") as handle:
                    handle.writelines(retained)
                os.replace(temporary, LOG_FILE)
        except Exception as error:
            debug(f"Could not update export log: {error}", "warning")

    def load_full_log(self):
        if LOG_FILE.exists():
            with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
                self.full_log_lines = f.readlines()[-MAX_LOG_ENTRIES:]
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

        filters = getattr(self, "log_filters", {})
        workspace = str(filters.get("workspace", "")).strip().casefold()
        date_from = str(filters.get("date_from", "")).strip()
        date_to = str(filters.get("date_to", "")).strip()
        if workspace:
            parsed = [p for p in parsed if workspace in self._extract_value(p["raw"], "Workspace").casefold()]
        if date_from:
            parsed = [p for p in parsed if p["date"] >= date_from]
        if date_to:
            parsed = [p for p in parsed if p["date"] <= date_to]

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

    def open_log_filters(self):
        popup = tk.Toplevel(self)
        popup.title("Filter Logs")
        popup.transient(self)
        popup.resizable(False, False)
        popup.grab_set()

        body = ctk.CTkFrame(popup)
        body.pack(fill="both", expand=True, padx=14, pady=14)
        ctk.CTkLabel(body, text="Filter Logs", font=(self.font_family, self.font_size + 2, "bold")).pack(anchor="w", pady=(0, 10))
        ctk.CTkLabel(body, text="Workspace name (partial match is okay)").pack(anchor="w")
        workspace_var = ctk.StringVar(value=self.log_filters.get("workspace", ""))
        CTkEntry(body, textvariable=workspace_var, width=310).pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(body, text="Export date from (YYYY-MM-DD)").pack(anchor="w")
        from_var = ctk.StringVar(value=self.log_filters.get("date_from", ""))
        CTkEntry(body, textvariable=from_var, width=310).pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(body, text="Export date through (YYYY-MM-DD)").pack(anchor="w")
        to_var = ctk.StringVar(value=self.log_filters.get("date_to", ""))
        CTkEntry(body, textvariable=to_var, width=310).pack(fill="x", pady=(0, 12))

        def apply_filters():
            self.log_filters = {"workspace": workspace_var.get().strip(), "date_from": from_var.get().strip(), "date_to": to_var.get().strip()}
            active = any(self.log_filters.values())
            self.log_filter_button.configure(text="⚲ Filters •" if active else "⚲ Filters")
            self.update_log_view()
            popup.destroy()

        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.pack(fill="x")
        ctk.CTkButton(buttons, text="Clear", command=lambda: (workspace_var.set(""), from_var.set(""), to_var.set(""))).pack(side="left")
        ctk.CTkButton(buttons, text="Apply", command=apply_filters).pack(side="right")
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
    def confirm_batch_workspace(self, file_count):
        """Confirm one workspace before a batch of PDFs is opened."""
        if file_count <= 1:
            return self.settings.get("default_workspace", "Accounting")

        available = list(WORKSPACES.keys()) or ["Accounting"]
        current = self.settings.get("default_workspace", "Accounting")
        if current not in available:
            current = available[0]

        dialog = tk.Toplevel(self)
        dialog.title("Choose Workspace")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        dialog.geometry("470x230")

        ctk.CTkLabel(
            dialog, text=f"Open {file_count} PDFs",
            font=(self.font_family, self.font_size + 3, "bold")
        ).pack(pady=(22, 6))
        ctk.CTkLabel(
            dialog,
            text="Choose the workspace that should be used for all of these files.",
            wraplength=410, justify="center", text_color="#888888"
        ).pack(padx=20, pady=(0, 14))

        workspace_var = ctk.StringVar(value=current)
        ctk.CTkOptionMenu(
            dialog, values=available, variable=workspace_var, width=230
        ).pack(pady=(0, 18))

        result = {"workspace": None}

        def cancel():
            result["workspace"] = None
            dialog.destroy()

        def accept():
            result["workspace"] = workspace_var.get()
            self.settings["default_workspace"] = result["workspace"]
            self.save_settings()
            dialog.destroy()

        buttons = ctk.CTkFrame(dialog, fg_color="transparent")
        buttons.pack(fill="x", padx=22, pady=(0, 16))
        ctk.CTkButton(buttons, text="Cancel", width=100, command=cancel).pack(side="right", padx=(8, 0))
        ctk.CTkButton(buttons, text="Open Files", width=110, command=accept).pack(side="right")
        dialog.protocol("WM_DELETE_WINDOW", cancel)
        dialog.after(60, dialog.focus_force)
        self.wait_window(dialog)
        return result["workspace"]

    def _rendered_pdf_sessions(self):
        return [
            session for session in self.pdf_sessions.values()
            if session.get("is_rendered", False)
        ]

    def _render_pdf_placeholder(self, session):
        """Keep a loaded PDF lightweight until the user selects its tab."""
        tab = session["tab"]
        for widget in tab.winfo_children():
            widget.destroy()

        session["is_rendered"] = False
        session["entries"] = []
        session["widgets_to_scale"] = []

        bubble_color, border_color = self.get_log_bubble_colors()
        bubble = ctk.CTkFrame(
            tab, fg_color=bubble_color, border_color=border_color,
            border_width=3, corner_radius=10
        )
        bubble.pack(fill="both", expand=True, padx=20, pady=20)
        range_status = (
            f"{len(session.get('ranges', []))} part(s) detected.\n"
            if session.get("ranges_ready", True)
            else "Split markers will be detected when you open this document.\n"
        )
        ctk.CTkLabel(
            bubble,
            text="This document is loaded but not currently rendered",
            font=(self.font_family, self.font_size + 3, "bold")
        ).pack(pady=(45, 10))
        ctk.CTkLabel(
            bubble,
            text=(f"{Path(session['path']).name}\n\n" + range_status
                  + "CleanCutPDF keeps only a few full editors active at once "
                  "so large batches remain responsive."),
            justify="center", text_color="#888888"
        ).pack(pady=(0, 18))
        ctk.CTkButton(
            bubble,
            text="Load Full Editor",
            command=lambda s=session: self._activate_pdf_session(s),
            width=170
        ).pack()

    def _unload_pdf_session_editor(self, session):
        if not session.get("is_rendered", False):
            return
        try:
            self.capture_workspace_data(session)
        except Exception as error:
            debug(f"Could not preserve fields before compacting tab: {error}", "warning")
        self._render_pdf_placeholder(session)
        debug(f"Compacted inactive PDF tab: {session.get('tab_label', '')}", "debug")

    def _activate_pdf_session(self, session):
        session_name = Path(session.get("path", "Unknown PDF")).name
        _record_last_action("Activate PDF session: start", session_name)
        if session.get("is_rendered", False):
            self.active_pdf_session = session
            self.pdf_tabview.set(session["tab_label"])
            _record_last_action("Activate PDF session: already rendered", session_name)
            return

        rendered = self._rendered_pdf_sessions()
        if len(rendered) >= MAX_RENDERED_PDF_TABS:
            active_label = self.pdf_tabview.get()
            candidates = [
                item for item in rendered
                if item is not session and item.get("tab_label") != active_label
            ]
            if candidates:
                self._unload_pdf_session_editor(candidates[0])

        self._ensure_pdf_session_ranges(session)
        _record_last_action("Activate PDF session: ranges ready", session_name)

        self.render_splitter_tab(session["tab"], session)
        _record_last_action("Activate PDF session: editor rendered", session_name)
        session["is_rendered"] = True
        self.active_pdf_session = session
        self.pdf_tabview.set(session["tab_label"])
        _record_last_action("Activate PDF session: complete", session_name)

    def _ensure_pdf_session_ranges(self, session):
        """Detect split markers only when a restored PDF is first opened."""
        if session.get("ranges_ready", True):
            return

        reader = session.get("reader")
        source_path = session.get("path")
        if reader is None or not source_path:
            return

        ranges = self.detect_split_ranges_from_reader(reader, source_path=source_path)
        session["ranges"] = ranges
        session["workspace_data"] = self.reconcile_workspace_data_ranges(
            session.get("workspace_data", {}), ranges
        )
        session["ranges_ready"] = True
        debug(
            f"Lazy split detection completed for {Path(source_path).name}: "
            f"{len(ranges)} range(s)",
            "debug"
        )

    def load_pdf(self):
        paths = filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
        valid_paths = [path for path in paths if path.lower().endswith(".pdf")]
        workspace_name = self.confirm_batch_workspace(len(valid_paths))
        if valid_paths and workspace_name is None:
            return
        for path in valid_paths:
            self.load_pdf_from_path(path, workspace_name=workspace_name)
    def load_pdf_from_path(self, path, render=True, workspace_name=None):
        pdf_name = Path(path).stem

        # Prevent duplicate loads
        if pdf_name in self.pdf_sessions:
            messagebox.showinfo("Already Loaded", f"{pdf_name} is already open.")
            return

        try:
            reader = PdfReader(path)
            ranges = self.detect_split_ranges_from_reader(reader, source_path=path)
            self.warn_if_no_split_markers(reader, path)

            pdf_name = Path(path).stem
            tab_label = f"{pdf_name} ✖"
            tab = self.pdf_tabview.add(tab_label)
            self._apply_tab_font_size()
            self.pdf_tabview.set(tab_label)

            if workspace_name not in WORKSPACES:
                workspace_name = self.settings.get("default_workspace", "Accounting")
            if workspace_name not in WORKSPACES:
                workspace_name = "Accounting"

            session = {
                "tab": tab,
                "tab_label": tab_label,
                "reader": reader,
                "path": Path(path),
                "folder_id": self._selected_pdf_folder_id(),
                "ranges": ranges,
                "entries": [],
                "client_name_var": ctk.StringVar(),
                "workspace": workspace_name,
                "workspace_data": {},
                "last_exported_files": [],
                "widgets_to_scale": []
            }

            self.pdf_sessions[pdf_name] = session
            self.pdf_project["selected_folder_id"] = session["folder_id"]

            self.update_idletasks()
            session["is_rendered"] = False
            self._activate_pdf_session(session)
            self._refresh_pdf_navigation()
            self._refresh_pdf_sidebar()

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
    def _is_split_marker_text(self, text):
        text = text or ""
        upper = text.upper()
        words = [w for w in re.findall(r"[A-Z0-9]+", upper) if w]
        compact = re.sub(r"[^A-Z]", "", upper)

        # Accept normal, spaced, hyphenated, or line-broken versions of SPLIT HERE.
        if "SPLITHERE" in compact:
            return True
        return "SPLIT" in words and "HERE" in words

    def _looks_like_visual_split_marker(self, fitz_page):
        """Recognize the colored SPLIT HERE sheet when a scan has no text layer.

        The printed separator is a nearly solid colored page with one short,
        wide line of dark text near the center. This intentionally conservative
        check avoids treating normal letters, statements, and photo pages as
        separators while covering scanners that intermittently omit OCR.
        """
        try:
            pix = fitz_page.get_pixmap(matrix=fitz.Matrix(0.65, 0.65), alpha=False)
            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            resampling = getattr(Image, "Resampling", Image).LANCZOS
            image = image.resize((240, 312), resampling)

            median = ImageStat.Stat(image).median
            background_range = max(median) - min(median)
            background_brightness = sum(median) / 3
            # White office documents are rejected here. Bright colored paper is
            # accepted by its channel spread; gray colored paper by brightness.
            colored_background = background_range >= 15 or background_brightness <= 238
            if not colored_background:
                return False

            flattened = getattr(image, "get_flattened_data", None)
            pixels = list(flattened() if callable(flattened) else image.getdata())
            uniform_count = sum(
                1 for pixel in pixels
                if all(abs(pixel[channel] - median[channel]) <= 30 for channel in range(3))
            )
            uniform_ratio = uniform_count / max(1, len(pixels))
            dark_count = sum(1 for pixel in pixels if max(pixel) < 120)
            dark_ratio = dark_count / max(1, len(pixels))
            if uniform_ratio < 0.82 or dark_ratio > 0.025:
                return False

            width, height = image.size
            left, right = int(width * 0.15), int(width * 0.85)
            top, bottom = int(height * 0.20), int(height * 0.80)
            dark_points = []
            for y in range(top, bottom):
                for x in range(left, right):
                    if max(image.getpixel((x, y))) < 120:
                        dark_points.append((x, y))

            if len(dark_points) < 70:
                return False
            min_x = min(point[0] for point in dark_points)
            max_x = max(point[0] for point in dark_points)
            min_y = min(point[1] for point in dark_points)
            max_y = max(point[1] for point in dark_points)
            text_width_ratio = (max_x - min_x + 1) / width
            text_height_ratio = (max_y - min_y + 1) / height
            text_center_y = ((min_y + max_y) / 2) / height

            matched = (
                0.25 <= text_width_ratio <= 0.72
                and 0.015 <= text_height_ratio <= 0.13
                and 0.32 <= text_center_y <= 0.68
            )
            if matched:
                debug(
                    "Visual split-marker fallback matched "
                    f"(uniform={uniform_ratio:.2f}, dark={dark_ratio:.3f}, "
                    f"text={text_width_ratio:.2f}x{text_height_ratio:.2f})",
                    "debug"
                )
            return matched
        except Exception as error:
            debug(f"Visual split-marker fallback failed: {error}", "warning")
            return False

    def detect_split_ranges_from_reader(self, reader, source_path=None):
        debug("Starting detect_split_ranges", "debug")
        split_pages = []
        fitz_doc = None

        if source_path:
            try:
                fitz_doc = fitz.open(str(source_path))
            except Exception as error:
                debug(f"PyMuPDF fallback could not open PDF: {error}", "warning")

        try:
            for idx, page in enumerate(reader.pages):
                text = ""
                fitz_page = None
                extraction_source = "PyPDF2"

                # PyMuPDF is substantially faster for the normal detection
                # path. If it is available, an empty text layer is handled by
                # the visual scan below instead of a second text extractor.
                if fitz_doc is not None and idx < fitz_doc.page_count:
                    try:
                        fitz_page = fitz_doc.load_page(idx)
                        fitz_text = fitz_page.get_text("text") or ""
                        text = fitz_text
                        extraction_source = "PyMuPDF"
                    except Exception as error:
                        debug(f"PyMuPDF text extraction failed on page {idx + 1}: {error}", "warning")

                # When PyMuPDF is available, an empty text layer is exactly
                # when the visual image scan should run. Calling PyPDF2 first
                # on every scanned page adds avoidable latency. Only use the
                # older extractor when PyMuPDF could not provide a page.
                if not text.strip() and fitz_page is None:
                    try:
                        text = page.extract_text() or ""
                        extraction_source = "PyPDF2"
                    except Exception as error:
                        debug(f"PyPDF2 text extraction failed on page {idx + 1}: {error}", "warning")

                marker_found = self._is_split_marker_text(text)

                # The visual fallback is expensive; only use it for pages with
                # no usable text layer, which is the case it was designed for.
                if not marker_found and fitz_page is not None and not text.strip():
                    if self._looks_like_visual_split_marker(fitz_page):
                        marker_found = True
                        extraction_source = "visual scan fallback"

                if marker_found:
                    debug(f"→ SPLIT marker found on page {idx + 1} using {extraction_source}", "debug")
                    split_pages.append(idx)
        finally:
            if fitz_doc is not None:
                try:
                    fitz_doc.close()
                except Exception:
                    pass

        self._last_split_marker_count = len(split_pages)

        ranges = []
        start = 0
        for split_page in split_pages:
            end = split_page - 1
            if start <= end:
                ranges.append({"start": start, "end": end})
            start = split_page + 1

        if start < len(reader.pages):
            ranges.append({"start": start, "end": len(reader.pages) - 1})
        if not ranges:
            ranges = [{"start": 0, "end": len(reader.pages) - 1}]

        debug(f"Detected {len(split_pages)} split marker(s); ranges: {ranges}", "debug")
        return ranges

    def warn_if_no_split_markers(self, reader, path=None):
        if getattr(self, "_last_split_marker_count", 0) != 0:
            return
        if len(reader.pages) <= 1:
            return
        if self.settings.get("suppressNoSplitWarning", False):
            return

        file_name = Path(path).name if path else "this PDF"
        popup = tk.Toplevel(self)
        popup.title("No Split Markers Detected")
        popup.transient(self)
        popup.grab_set()
        popup.resizable(False, False)
        popup.attributes("-topmost", True)

        width = 520
        height = 245
        self.update_idletasks()
        x = self.winfo_rootx() + max(0, (self.winfo_width() - width) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - height) // 2)
        popup.geometry(f"{width}x{height}+{x}+{y}")

        bubble_color, border_color = self.get_log_bubble_colors()
        frame = ctk.CTkFrame(
            popup, fg_color=bubble_color, border_color=border_color,
            border_width=2, corner_radius=10
        )
        frame.pack(fill="both", expand=True, padx=14, pady=14)

        ctk.CTkLabel(
            frame,
            text="No SPLIT HERE pages were detected",
            font=(self.font_family, self.font_size + 2, "bold")
        ).pack(pady=(18, 8))

        ctk.CTkLabel(
            frame,
            text=(
                f"CleanCutPDF did not detect any SPLIT HERE pages in {file_name}.\n\n"
                "The PDF will be loaded as one part. If SPLIT HERE sheets are visible in the scan, "
                "the scanner may not have created a readable text/OCR layer."
            ),
            wraplength=455,
            justify="center",
            font=(self.font_family, self.font_size)
        ).pack(padx=18, pady=(0, 10))

        suppress_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            frame,
            text="Do not display this warning again",
            variable=suppress_var
        ).pack(pady=(0, 12))

        def close_warning():
            if suppress_var.get():
                self.settings["suppressNoSplitWarning"] = True
                self.save_settings()
                if hasattr(self, "no_split_warning_var"):
                    self.no_split_warning_var.set(False)
                debug("No-split warning suppressed by user", "saved")
            try:
                popup.grab_release()
            except tk.TclError:
                pass
            popup.destroy()

        ctk.CTkButton(frame, text="Continue", width=110, command=close_warning).pack(pady=(0, 14))
        popup.protocol("WM_DELETE_WINDOW", close_warning)
        popup.after(60, popup.focus_force)
        self.wait_window(popup)

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

    def handle_drop(self, event):
        paths = self.parse_dropped_paths(event.data)
        valid_files = [p for p in paths if Path(p).suffix.lower() == ".pdf"]
        if not valid_files:
            messagebox.showerror("Invalid File(s)", "Only PDF files are supported.")
            return

        workspace_name = self.confirm_batch_workspace(len(valid_files))
        if workspace_name is None:
            return

        for path in valid_files:
            self.load_pdf_from_path(path, workspace_name=workspace_name)

        self.enable_tab_closing()
    def export_current_pdf(self):
        self.export_active_session()
    def parse_flexible_date(self, raw_value):
        raw = str(raw_value or "").strip()
        if not raw:
            raise ValueError("Date is blank")

        formats = (
            "%m%d%y", "%m%d%Y", "%m-%d-%Y", "%m/%d/%Y",
            "%Y.%m.%d", "%Y-%m-%d", "%Y/%m/%d"
        )
        for fmt in formats:
            try:
                return datetime.datetime.strptime(raw, fmt).date()
            except ValueError:
                pass
        raise ValueError(
            "Date must be a valid date such as 082026, 08-20-2026, 8-20-2026, or 2026.08.20"
        )

    def format_date_for_field(self, raw_value, field):
        date_obj = self.parse_flexible_date(raw_value)
        fmt = field.get("date_format", "M-D-YYYY")
        if fmt == "MM-DD-YYYY":
            return f"{date_obj.month:02d}-{date_obj.day:02d}-{date_obj.year}"
        if fmt == "YYYY.MM.DD":
            return f"{date_obj.year}.{date_obj.month:02d}.{date_obj.day:02d}"
        if fmt == "MMDDYY":
            return date_obj.strftime("%m%d%y")
        return f"{date_obj.month}-{date_obj.day:02d}-{date_obj.year}"

    def today_value_for_field(self, field):
        today = datetime.date.today()
        fmt = field.get("date_format", "M-D-YYYY")
        if fmt == "MM-DD-YYYY":
            return f"{today.month:02d}-{today.day:02d}-{today.year}"
        if fmt == "YYYY.MM.DD":
            return f"{today.year}.{today.month:02d}.{today.day:02d}"
        if fmt == "MMDDYY":
            return today.strftime("%m%d%y")
        return f"{today.month}-{today.day:02d}-{today.year}"

    def format_currency_value(self, raw_value):
        raw = str(raw_value or "").strip()
        if not raw:
            return ""
        cleaned = raw.upper().replace("USD", "").replace("$", "").replace(",", "").strip()
        try:
            amount = Decimal(cleaned).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            raise ValueError("Currency must be a number such as 134.06")
        return f"${amount:,.2f}"

    def field_is_visible(self, entry, field):
        condition = field.get("condition")
        if not isinstance(condition, dict):
            return True
        controller_key = condition.get("field")
        expected = str(condition.get("equals", ""))
        controller = entry.get("field_vars", {}).get(controller_key)
        if controller is None:
            return False
        try:
            actual = controller.get()
        except Exception:
            return False
        if isinstance(actual, bool):
            actual = "True" if actual else "False"
        return str(actual).strip().casefold() == expected.strip().casefold()

    def refresh_entry_conditional_fields(self, entry, profile):
        """Show/hide conditional fields without changing their layout manager.

        Automatic/legacy layouts use grid(), while the visual Workspace Designer
        uses place(). Calling grid() on a placed tile destroys its saved freeform
        geometry, so remember the manager for each field and restore it using the
        matching geometry system.
        """
        managers = entry.get("field_layout_managers", {})
        place_info = entry.get("field_place_info", {})

        for field in profile.get("fields", []):
            key = field.get("key")
            container = entry.get("field_containers", {}).get(key)
            if container is None:
                continue

            visible = self.field_is_visible(entry, field)
            entry.setdefault("field_visibility", {})[key] = visible
            manager = managers.get(key, "grid")

            try:
                if manager == "place":
                    if visible:
                        geometry = place_info.get(key)
                        if geometry:
                            container.place(**geometry)
                    else:
                        container.place_forget()
                else:
                    if visible:
                        container.grid()
                    else:
                        container.grid_remove()
            except tk.TclError:
                pass

    def render_workspace_note(self, parent, note, row):
        text = str(note.get("text", "")).strip()
        if not text:
            return row

        note_frame = ctk.CTkFrame(parent, fg_color="transparent")
        note_frame.grid(row=row, column=0, sticky="ew", padx=12, pady=(4, 3))
        note_font = ctk.CTkFont(
            family=self.font_family,
            size=max(10, self.font_size - 1),
            slant="italic"
        )
        note_label = ctk.CTkLabel(
            note_frame,
            text=text,
            font=note_font,
            text_color="#888888",
            wraplength=455,
            justify="left",
            anchor="w"
        )
        note_label._cleancut_note_label = True
        note_label.pack(fill="x")
        return row + 1

    def render_inline_workspace_note(self, parent, note):
        """Render a field-specific reminder directly below that field's title."""
        text = str(note.get("text", "")).strip()
        if not text:
            return
        note_font = ctk.CTkFont(
            family=self.font_family,
            size=max(10, self.font_size - 1),
            slant="italic"
        )
        note_label = ctk.CTkLabel(
            parent,
            text=text,
            font=note_font,
            text_color="#888888",
            wraplength=455,
            justify="left",
            anchor="w"
        )
        note_label._cleancut_note_label = True
        note_label.pack(anchor="w", fill="x", padx=12, pady=(0, 2))

    def render_splitter_tab(self, tab_frame, session):
        for widget in tab_frame.winfo_children():
            widget.destroy()

        session["is_rendered"] = True
        session["entries"] = []
        session["widgets_to_scale"] = []
        ranges = session["ranges"]

        workspace_name = session.get("workspace", self.settings.get("default_workspace", "Accounting"))
        if workspace_name not in WORKSPACES:
            workspace_name = "Accounting"
        session["workspace"] = workspace_name
        profile = self.get_workspace_profile(workspace_name)

        bubble_color, border_color = self.get_log_bubble_colors()
        bubble = ctk.CTkFrame(
            tab_frame, fg_color=bubble_color, border_color=border_color,
            border_width=3, corner_radius=10
        )
        bubble.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            bubble, text="📝 Rename Only" if session.get("rename_only") else "🧩 Split & Rename",
            font=(self.font_family, self.font_size + 4, "bold"),
            text_color="#3B8ED0"
        ).pack(pady=(10, 4))
        ctk.CTkLabel(
            bubble,
            text=f"📄 {Path(session['path']).name}",
            font=(self.font_family, self.font_size + 1, "bold"),
            text_color="#666666",
            wraplength=900,
            justify="center"
        ).pack(pady=(0, 8))

        workspace_row = ctk.CTkFrame(bubble, fg_color="transparent")
        workspace_row.pack(pady=(0, 4))
        workspace_label = ctk.CTkLabel(
            workspace_row, text="Workspace:",
            font=(self.font_family, self.font_size, "bold")
        )
        workspace_label.pack(side="left", padx=(0, 8))
        session["workspace_var"] = ctk.StringVar(value=workspace_name)
        workspace_menu = ctk.CTkOptionMenu(
            workspace_row, values=list(WORKSPACES.keys()),
            variable=session["workspace_var"],
            command=lambda selected, s=session: self.change_session_workspace(s, selected),
            width=170
        )
        workspace_menu.pack(side="left")
        session["widgets_to_scale"].extend([workspace_label, workspace_menu])

        ctk.CTkLabel(
            bubble, text=profile.get("summary", ""),
            font=(self.font_family, max(10, self.font_size - 2)),
            text_color="#888888", wraplength=820, justify="center"
        ).pack(pady=(0, 6))

        content = ctk.CTkFrame(bubble)
        content.pack(fill="both", expand=True, padx=10, pady=10)

        custom_layout = profile.get("custom_layout") if isinstance(profile.get("custom_layout"), dict) else None
        freeform_workspace = bool(
            custom_layout and custom_layout.get("enabled") and int(custom_layout.get("version", 1)) >= 2
        )

        # The PDF viewer is intentionally static and singular. Custom workspace
        # layouts control only the field tiles on the left.
        form_frame = ctk.CTkScrollableFrame(content, width=620)
        form_frame.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=6)
        session["parts_frame"] = form_frame

        client_box = ctk.CTkFrame(form_frame, fg_color="transparent")
        client_box.pack(pady=(10, 10), padx=10, anchor="w", fill="x")
        name_label = ctk.CTkLabel(client_box, text=f"{profile.get('client_label', 'Client Name')} (optional):")
        name_label.pack(side="left", anchor="n", pady=(7, 0))
        session["widgets_to_scale"].append(name_label)

        info_icon = ctk.CTkLabel(client_box, text="❓", text_color="#888888", cursor="question_arrow")
        info_icon.pack(side="left", anchor="n", padx=(5, 10), pady=(7, 0))
        self.add_tooltip(
            info_icon,
            "Client suggestions come from folders in the output location. Press Tab to accept the highlighted match."
        )

        name_column = ctk.CTkFrame(client_box, fg_color="transparent", width=300)
        name_column.pack(side="left", anchor="n")

        name_entry = CTkEntry(
            name_column,
            textvariable=session["client_name_var"],
            width=300,
            placeholder_text="Type to search output folders"
        )
        name_entry.pack(fill="x")
        session["client_name_entry"] = name_entry
        session["widgets_to_scale"].append(name_entry)

        list_bg, list_fg, list_select_bg, list_select_fg = self._filename_editor_colors()
        suggestion_listbox = tk.Listbox(
            name_column,
            height=3,
            exportselection=False,
            activestyle="none",
            font=(self.font_family, self.font_size),
            bg=list_bg,
            fg=list_fg,
            selectbackground=list_select_bg,
            selectforeground=list_select_fg,
            relief="solid",
            borderwidth=1,
            highlightthickness=0,
            takefocus=False
        )
        session["client_suggestion_listbox"] = suggestion_listbox

        suggestion_listbox.bind(
            "<ButtonRelease-1>",
            lambda _event, s=session, w=name_entry: self.accept_client_suggestion(s, w)
        )
        suggestion_listbox.bind(
            "<Return>",
            lambda _event, s=session, w=name_entry: self.accept_client_suggestion(s, w)
        )
        suggestion_listbox.bind(
            "<Tab>",
            lambda _event, s=session, w=name_entry: self.accept_client_suggestion(s, w)
        )
        ctk.CTkButton(
            client_box, text="Aa", width=38,
            command=lambda s=session: self.force_title_case_client_name(s)
        ).pack(side="left", anchor="n", padx=(6, 0))
        self.add_tooltip(client_box.winfo_children()[-1], "Convert the current client name to title case.")
        # Bind the real tkinter Entry inside CustomTkinter. Binding the outer
        # CTkEntry frame does not receive typing events on every platform.
        name_entry_control = getattr(name_entry, "_entry", name_entry)
        name_entry_control.bind(
            "<KeyRelease>",
            lambda event, s=session, w=name_entry: (
                None if event.keysym in {"Tab", "Return", "Escape", "Up", "Down"}
                else self.show_client_suggestions(s, w)
            ),
            add="+"
        )
        name_entry_control.bind(
            "<Tab>",
            lambda _event, s=session, w=name_entry: self.accept_client_suggestion(s, w),
            add="+"
        )
        name_entry_control.bind("<Down>", lambda _event: self.move_client_suggestion(1), add="+")
        name_entry_control.bind("<Up>", lambda _event: self.move_client_suggestion(-1), add="+")
        name_entry_control.bind(
            "<FocusOut>",
            lambda _event: self.after(150, self.hide_client_suggestions),
            add="+"
        )

        for part_index, r in enumerate(ranges):
            part_number = part_index + 1
            part_card = ctk.CTkFrame(form_frame, fg_color=bubble_color, corner_radius=10)
            part_card.pack(fill="x", padx=10, pady=(0, 10))

            header = ctk.CTkFrame(part_card, fg_color="transparent")
            header.pack(fill="x", pady=(10, 0), padx=10)
            part_title = ctk.CTkLabel(
                header,
                text=(
                    f"File — Pages {r['start'] + 1} to {r['end'] + 1}"
                    if session.get("rename_only")
                    else f"Part {part_number} — Pages {r['start'] + 1} to {r['end'] + 1}"
                ),
                font=(self.font_family, self.font_size + 1, "bold"),
                text_color="#3B8ED0",
                cursor="hand2"
            )
            part_title.pack(side="left")
            part_title.bind(
                "<Button-1>",
                lambda _event, s=session, page=r["start"], pi=part_index: self.jump_pdf_preview_to_page(s, page, pi)
            )
            self.add_tooltip(part_title, f"Click to preview page {r['start'] + 1}")
            session["widgets_to_scale"].append(part_title)

            entry = {
                "range": r,
                "field_vars": {},
                "field_widgets": {},
                "field_containers": {},
                "field_visibility": {},
                "field_layout_managers": {},
                "field_place_info": {},
                "choice_display_vars": {},
                "choice_other_vars": {}
            }
            session["entries"].append(entry)

            # Header toggles / checkboxes remain in the legacy header only while
            # the workspace is using the automatic layout. In a custom layout,
            # every assigned field (including Revoked/toggles) becomes movable.
            for field in profile.get("fields", []):
                if custom_layout and custom_layout.get("enabled"):
                    continue
                if field.get("placement") != "header":
                    continue
                key = field["key"]
                default = self.get_workspace_field_default(workspace_name, field)
                saved = self.get_workspace_saved_value(session, workspace_name, part_index, key, default)
                variable = ctk.BooleanVar(value=bool(saved))
                field_color = self.get_field_color(field)
                if field.get("type") == "checkbox":
                    widget = ctk.CTkCheckBox(header, text=field["label"], variable=variable)
                    if field_color:
                        widget.configure(text_color=field_color, border_color=field_color, fg_color=field_color)
                else:
                    widget = ctk.CTkSwitch(header, text=field["label"], variable=variable)
                    if field_color:
                        widget.configure(text_color=field_color, progress_color=field_color)
                widget.pack(side="right", padx=(8, 0))
                entry["field_vars"][key] = variable
                entry["field_widgets"][key] = widget
                entry[key] = variable
                session["widgets_to_scale"].append(widget)

            fields_frame = ctk.CTkFrame(part_card, fg_color="transparent")
            fields_frame.pack(fill="x", padx=0, pady=(4, 6))
            freeform_layout = bool(custom_layout and custom_layout.get("enabled") and int(custom_layout.get("version", 1)) >= 2)
            if freeform_layout:
                # A freeform workspace should be sized from the tiles that are actually
                # being used, NOT from the whole designer window. Earlier builds saved
                # the entire large canvas as the surface, so a small cluster of fields
                # in the upper-left got dramatically shrunk at runtime.
                raw_elements = custom_layout.get("elements", {}) if isinstance(custom_layout.get("elements"), dict) else {}
                active_keys = {field.get("key") for field in profile.get("fields", []) if field.get("key")}
                active_boxes = [
                    box for key, box in raw_elements.items()
                    if key in active_keys and isinstance(box, dict)
                ]

                layout_pad = 24
                if active_boxes:
                    try:
                        min_x = min(max(0, int(box.get("x", 0))) for box in active_boxes)
                        min_y = min(max(0, int(box.get("y", 0))) for box in active_boxes)
                        max_right = max(
                            max(0, int(box.get("x", 0))) + max(120, int(box.get("width", 240)))
                            for box in active_boxes
                        )
                        max_bottom = max(
                            max(0, int(box.get("y", 0))) + max(84, int(box.get("height", 84)))
                            for box in active_boxes
                        )
                    except Exception:
                        min_x, min_y, max_right, max_bottom = 0, 0, 640, 420
                else:
                    min_x, min_y, max_right, max_bottom = 0, 0, 640, 420

                layout_origin_x = min_x - layout_pad
                layout_origin_y = min_y - layout_pad
                layout_surface_w = max(320, (max_right - min_x) + layout_pad * 2)
                layout_surface_h = max(120, (max_bottom - min_y) + layout_pad * 2)
                surface_ratio = layout_surface_h / max(1, layout_surface_w)

                # The runtime may have much less vertical room than the designer.
                # Guarantee that every placed tile still receives enough physical
                # pixels for its label and input. Expanding the whole surface also
                # expands the spacing between rows, so tiles never paint over one
                # another.
                field_by_key = {
                    field.get("key"): field
                    for field in profile.get("fields", [])
                    if field.get("key")
                }
                minimum_runtime_surface_h = 150
                for field_key, box in raw_elements.items():
                    if field_key not in active_keys or not isinstance(box, dict):
                        continue
                    try:
                        saved_height = max(1, int(box.get("height", 84)))
                    except Exception:
                        saved_height = 84
                    tile_minimum = self.get_freeform_tile_min_height(field_by_key.get(field_key))
                    required_surface = int((tile_minimum * layout_surface_h) / saved_height) + 1
                    minimum_runtime_surface_h = max(minimum_runtime_surface_h, required_surface)

                # Store the normalized bounds on the frame so every tile uses the
                # exact same coordinate system below.
                fields_frame._layout_origin_x = layout_origin_x
                fields_frame._layout_origin_y = layout_origin_y
                fields_frame._layout_surface_w = layout_surface_w
                fields_frame._layout_surface_h = layout_surface_h
                fields_frame._layout_min_runtime_height = minimum_runtime_surface_h

                initial_surface_h = max(
                    150,
                    minimum_runtime_surface_h,
                    int(620 * surface_ratio)
                )
                fields_frame.configure(height=min(2400, initial_surface_h))
                fields_frame.pack_propagate(False)

                def _keep_custom_surface_aspect(
                    event,
                    frame=fields_frame,
                    ratio=surface_ratio,
                    minimum_height=minimum_runtime_surface_h
                ):
                    try:
                        if event.width <= 1:
                            return
                        desired = max(minimum_height, int(round(event.width * ratio)))
                        desired = max(150, min(2400, desired))
                        if abs(frame.winfo_height() - desired) > 2:
                            frame.configure(height=desired)
                    except tk.TclError:
                        pass

                fields_frame.bind("<Configure>", _keep_custom_surface_aspect, add="+")
            else:
                for grid_col in range(3):
                    fields_frame.grid_columnconfigure(grid_col, weight=1)

            standard_fields = (list(profile.get("fields", [])) if custom_layout and custom_layout.get("enabled") else [f for f in profile.get("fields", []) if f.get("placement") != "header"])
            workspace_notes = profile.get("notes", [])
            field_row = 0
            if not (custom_layout and custom_layout.get("enabled")):
                for note in workspace_notes:
                    if note.get("before_field") == "__top__":
                        field_row = self.render_workspace_note(fields_frame, note, field_row)

            for field in standard_fields:
                key = field["key"]
                field_type = field.get("type", "text")
                default = self.get_workspace_field_default(workspace_name, field)
                saved = self.get_workspace_saved_value(session, workspace_name, part_index, key, default)
                if (
                    field.get("type") == "date"
                    and field.get("auto_today", False)
                    and not str(saved or "").strip()
                ):
                    saved = self.today_value_for_field(field)

                outer = ctk.CTkFrame(fields_frame, fg_color="transparent")
                if freeform_layout:
                    box = custom_layout.get("elements", {}).get(key, {}) if isinstance(custom_layout.get("elements"), dict) else {}
                    try:
                        x = max(0, int(box.get("x", 20)))
                        y = max(0, int(box.get("y", field_row * 82 + 30)))
                        width = max(120, int(box.get("width", 420)))
                        height = max(72, int(box.get("height", 84)))
                    except Exception:
                        x, y, width, height = 20, field_row * 92 + 30, 420, 84

                    origin_x = getattr(fields_frame, "_layout_origin_x", 0)
                    origin_y = getattr(fields_frame, "_layout_origin_y", 0)
                    runtime_surface_w = max(1, getattr(fields_frame, "_layout_surface_w", 640))
                    runtime_surface_h = max(1, getattr(fields_frame, "_layout_surface_h", 420))

                    # Map only the USED designer area into the Part card. This keeps
                    # the visual proportions the user actually arranged instead of
                    # shrinking them to account for unused empty canvas space.
                    geometry = {
                        "relx": (x - origin_x) / runtime_surface_w,
                        "rely": (y - origin_y) / runtime_surface_h,
                        "relwidth": min(1.0, width / runtime_surface_w),
                        "relheight": min(1.0, height / runtime_surface_h)
                    }
                    outer.place(**geometry)
                    entry["field_layout_managers"][key] = "place"
                    entry["field_place_info"][key] = geometry
                elif custom_layout and custom_layout.get("enabled"):
                    position = custom_layout.get("field_positions", {}).get(key, {})
                    grid_row = int(position.get("row", field_row))
                    grid_col = max(0, min(2, int(position.get("col", 0))))
                    grid_span = max(1, min(3 - grid_col, int(position.get("span", 3))))
                    outer.grid(row=grid_row, column=grid_col, columnspan=grid_span, sticky="ew", padx=3, pady=2)
                    entry["field_layout_managers"][key] = "grid"
                else:
                    outer.grid(row=field_row, column=0, columnspan=3, sticky="ew", padx=0, pady=0)
                    entry["field_layout_managers"][key] = "grid"
                entry["field_containers"][key] = outer

                label_row = ctk.CTkFrame(outer, fg_color="transparent")
                if freeform_layout:
                    # Give labels their own fixed band at the top of the tile so
                    # they can never overlap the input control below.
                    label_row.place(relx=0.02, rely=0.03, relwidth=0.96, relheight=0.31)
                    label_row.pack_propagate(False)
                else:
                    label_row.pack(anchor="w", padx=12, pady=(6, 0), fill="x")
                display_label = field.get("label", key.replace("_", " ").title())
                if field_type == "date":
                    display_label = f"{display_label} ({field.get('date_format', 'M-D-YYYY')})"
                if field.get("required"):
                    display_label += " *"
                field_color = self.get_field_color(field)
                label_kwargs = {"text": display_label}
                if field_color:
                    label_kwargs["text_color"] = field_color
                label = ctk.CTkLabel(label_row, **label_kwargs)
                label.pack(side="left")
                session["widgets_to_scale"].append(label)

                tooltip = field.get("tooltip")
                if tooltip:
                    tip_icon = ctk.CTkLabel(label_row, text="❓", text_color="#888888", cursor="question_arrow")
                    tip_icon.pack(side="left", padx=(5, 0))
                    self.add_tooltip(tip_icon, tooltip)

                # Field-targeted reminders belong directly below the field title.
                field_notes = [note for note in workspace_notes if note.get("before_field") == key]
                has_field_notes = bool(field_notes)
                if freeform_layout and has_field_notes:
                    note_text = "\n".join(str(note.get("text", "")).strip() for note in field_notes if str(note.get("text", "")).strip())
                    if note_text:
                        note_font = ctk.CTkFont(
                            family=self.font_family,
                            size=max(10, self.font_size - 1),
                            slant="italic"
                        )
                        inline_note = ctk.CTkLabel(
                            outer, text=note_text, font=note_font, text_color="#888888",
                            justify="left", anchor="w", wraplength=max(100, int(width * 0.90))
                        )
                        inline_note._cleancut_note_label = True
                        inline_note.place(relx=0.02, rely=0.30, relwidth=0.96, relheight=0.20)
                elif has_field_notes:
                    for note in field_notes:
                        self.render_inline_workspace_note(outer, note)

                control_rely = 0.52 if freeform_layout and has_field_notes else 0.40
                control_relheight = 0.45 if freeform_layout and has_field_notes else 0.56

                if field_type in {"checkbox", "toggle", "bool"}:
                    variable = ctk.BooleanVar(value=bool(saved))
                    control_parent = outer
                    if freeform_layout:
                        control_parent = ctk.CTkFrame(outer, fg_color="transparent")
                        control_parent.place(relx=0.02, rely=control_rely, relwidth=0.96, relheight=control_relheight)
                        control_parent.pack_propagate(False)
                    if field_type == "checkbox":
                        widget = ctk.CTkCheckBox(control_parent, text="", variable=variable)
                        if field_color:
                            widget.configure(border_color=field_color, fg_color=field_color)
                    else:
                        widget = ctk.CTkSwitch(control_parent, text="", variable=variable)
                        if field_color:
                            widget.configure(progress_color=field_color)
                    if freeform_layout:
                        widget.pack(anchor="w", padx=4, pady=4)
                    else:
                        widget.pack(anchor="w", padx=12, pady=(2, 8))

                elif field_type == "choice":
                    options = [str(option) for option in field.get("options", []) if str(option).strip()]
                    if not options:
                        options = ["Other"]
                    menu_options = ["Select..."] + options
                    saved_text = str(saved or "")
                    other_enabled = any(option.casefold() == "other" for option in options)
                    other_option = next((option for option in options if option.casefold() == "other"), "Other")

                    effective_var = ctk.StringVar(value=saved_text)
                    if saved_text in options:
                        initial_display = saved_text
                        initial_other = ""
                    elif saved_text and other_enabled:
                        initial_display = other_option
                        initial_other = saved_text
                    else:
                        initial_display = "Select..."
                        initial_other = ""
                        effective_var.set("")

                    display_var = ctk.StringVar(value=initial_display)
                    other_var = ctk.StringVar(value=initial_other)
                    choice_row = ctk.CTkFrame(outer, fg_color="transparent")
                    if freeform_layout:
                        # Reserve the lower half of the tile for the actual input.
                        # Using place here prevents the pack manager from shrinking
                        # the row back down to the control's minimum requested size.
                        choice_row.place(relx=0.02, rely=control_rely, relwidth=0.96, relheight=control_relheight)
                        choice_row.pack_propagate(False)
                    else:
                        choice_row.pack(fill="x", padx=12, pady=(0, 5))
                    choice_menu_kwargs = {
                        "values": menu_options,
                        "variable": display_var
                    }
                    choice_menu = ctk.CTkOptionMenu(choice_row, **choice_menu_kwargs)
                    if field_color:
                        choice_menu.configure(button_color=field_color)
                    choice_menu.pack(side="left", fill="both", expand=True)
                    other_entry_kwargs = {
                        "textvariable": other_var,
                        "placeholder_text": "Other..."
                    }
                    other_entry = CTkEntry(choice_row, **other_entry_kwargs)

                    if freeform_layout:
                        def _fit_choice_controls(event, controls=(choice_menu, other_entry)):
                            height = max(28, int(event.height))
                            for control in controls:
                                try:
                                    control.configure(height=height)
                                except (tk.TclError, ValueError):
                                    pass
                        choice_row.bind("<Configure>", _fit_choice_controls, add="+")

                    sync_guard = {"busy": False}
                    def update_effective_from_display(selected=None, ev=effective_var, dv=display_var,
                                                      ov=other_var, oe=other_entry, other_name=other_option,
                                                      guard=sync_guard):
                        if guard["busy"]:
                            return
                        guard["busy"] = True
                        try:
                            selected_value = selected if selected is not None else dv.get()
                            if str(selected_value) == "Select...":
                                if oe.winfo_manager():
                                    oe.pack_forget()
                                ev.set("")
                            elif str(selected_value).casefold() == str(other_name).casefold():
                                if not oe.winfo_manager():
                                    oe.pack(side="left", fill="both", expand=True, padx=(8, 0))
                                ev.set(ov.get())
                            else:
                                if oe.winfo_manager():
                                    oe.pack_forget()
                                ev.set(selected_value)
                        finally:
                            guard["busy"] = False

                    choice_menu.configure(command=update_effective_from_display)
                    other_var.trace_add("write", lambda *_a, ev=effective_var, dv=display_var, ov=other_var, other_name=other_option:
                                        ev.set(ov.get()) if dv.get().casefold() == other_name.casefold() else None)

                    def sync_display_from_effective(*_a, ev=effective_var, dv=display_var, ov=other_var,
                                                    opts=options, other_name=other_option, oe=other_entry,
                                                    other_is_enabled=other_enabled, guard=sync_guard):
                        if guard["busy"]:
                            return
                        value = str(ev.get())
                        guard["busy"] = True
                        try:
                            if not value:
                                dv.set("Select...")
                                if oe.winfo_manager():
                                    oe.pack_forget()
                            elif value in opts:
                                dv.set(value)
                                if oe.winfo_manager():
                                    oe.pack_forget()
                            elif other_is_enabled:
                                dv.set(other_name)
                                ov.set(value)
                                if not oe.winfo_manager():
                                    oe.pack(side="left", fill="both", expand=True, padx=(8, 0))
                            else:
                                dv.set(value)
                        finally:
                            guard["busy"] = False

                    effective_var.trace_add("write", sync_display_from_effective)
                    update_effective_from_display(display_var.get())
                    variable = effective_var
                    widget = choice_menu
                    entry["choice_display_vars"][key] = display_var
                    entry["choice_other_vars"][key] = other_var

                else:
                    variable = ctk.StringVar(value=str(saved) if saved is not None else "")
                    input_row = ctk.CTkFrame(outer, fg_color="transparent")
                    if freeform_layout:
                        # In a tiled workspace the tile owns the height. Place a
                        # dedicated input row in the lower portion and make its
                        # children fill that row. This fixes the skinny one-line
                        # controls that remained even when CTkEntry(height=...) was set.
                        input_row.place(relx=0.02, rely=control_rely, relwidth=0.96, relheight=control_relheight)
                        input_row.pack_propagate(False)
                    else:
                        input_row.pack(fill="x", padx=12, pady=(0, 5 if field_type != "date" else 8))
                    entry_kwargs = {
                        "textvariable": variable,
                        "placeholder_text": field.get("placeholder", "")
                    }
                    if field_color:
                        entry_kwargs["border_color"] = field_color
                    widget = CTkEntry(input_row, **entry_kwargs)

                    row_controls = []
                    if field_type == "date":
                        today_kwargs = {
                            "text": "Today",
                            "width": 70,
                            "command": lambda v=variable, f=field: v.set(self.today_value_for_field(f))
                        }
                        if field_color:
                            today_kwargs["fg_color"] = field_color
                            today_kwargs["text_color"] = self.contrast_text_for_hex(field_color)
                        today_button = ctk.CTkButton(input_row, **today_kwargs)
                        today_button.pack(side="left", fill="y", padx=(0, 8))
                        row_controls.append(today_button)

                    widget.pack(side="left", fill="both", expand=True)
                    row_controls.append(widget)

                    if freeform_layout:
                        def _fit_input_controls(event, controls=tuple(row_controls)):
                            height = max(28, int(event.height))
                            for control in controls:
                                try:
                                    control.configure(height=height)
                                except (tk.TclError, ValueError):
                                    pass
                        input_row.bind("<Configure>", _fit_input_controls, add="+")

                    if field_type == "currency":
                        def normalize_currency(_event=None, v=variable):
                            raw = v.get().strip()
                            if not raw:
                                return
                            try:
                                v.set(self.format_currency_value(raw))
                            except ValueError:
                                # Leave the raw value in place so export can give a precise error.
                                pass
                        widget.bind("<FocusOut>", normalize_currency)

                entry["field_vars"][key] = variable
                entry["field_widgets"][key] = widget
                entry[key] = variable
                session["widgets_to_scale"].append(widget)
                field_row += 1

            if freeform_layout:
                # Keep reminder notes visible below the freeform field surface. Notes
                # are still managed by the Workspace Notes editor and can be made
                # draggable in a later designer pass without losing today's behavior.
                if workspace_notes:
                    notes_below = ctk.CTkFrame(part_card, fg_color="transparent")
                    notes_below.pack(fill="x", padx=0, pady=(0, 6))
                    notes_below.grid_columnconfigure(0, weight=1)
                    note_row = 0
                    for note in workspace_notes:
                        if note.get("before_field") in {"__top__", "__end__"}:
                            note_row = self.render_workspace_note(notes_below, note, note_row)
            elif custom_layout and custom_layout.get("enabled"):
                positions = custom_layout.get("field_positions", {})
                max_row = max([int(pos.get("row", 0)) for pos in positions.values() if isinstance(pos, dict)] + [0]) + 1
                note_row = max_row
                for note in workspace_notes:
                    if note.get("before_field") in {"__top__", "__end__"}:
                        note_row = self.render_workspace_note(fields_frame, note, note_row)
            else:
                for note in workspace_notes:
                    if note.get("before_field") == "__end__":
                        field_row = self.render_workspace_note(fields_frame, note, field_row)

            # Autofill is attached only after every part has its variables.
            # For the current part, delay until the whole session loop is finished.

        # Attach traces now that every part contains every assigned field.
        for part_index, entry in enumerate(session["entries"]):
            for field in profile.get("fields", []):
                key = field["key"]
                variable = entry.get("field_vars", {}).get(key)
                if variable is None:
                    continue
                if field.get("autofill", False):
                    variable.trace_add(
                        "write",
                        self.make_autofill_handler(key, variable, part_index, session["entries"])
                    )

            # Any controlling field can affect visibility of one or more fields.
            controller_keys = {
                field.get("condition", {}).get("field")
                for field in profile.get("fields", [])
                if isinstance(field.get("condition"), dict)
            }
            for controller_key in controller_keys:
                controller = entry.get("field_vars", {}).get(controller_key)
                if controller is not None:
                    controller.trace_add(
                        "write",
                        lambda *_a, e=entry, p=profile: self.refresh_entry_conditional_fields(e, p)
                    )
            self.refresh_entry_conditional_fields(entry, profile)

        # One static PDF viewer for the entire session. It does not repeat per
        # Part and is not controlled by the Workspace Designer.
        preview_frame = ctk.CTkFrame(content, width=520)
        preview_frame.pack_propagate(False)
        preview_frame.pack(side="right", fill="y", padx=(10, 0), pady=10)
        self.render_pdf_preview(session, preview_frame, page_index=session.get("preview_page_index", 0))

        make_folder = ctk.CTkCheckBox(bubble, text="Make Client Folder", variable=self.make_client_folder_var)
        make_folder.pack(pady=(5, 0))
        session["widgets_to_scale"].append(make_folder)

        button_row = ctk.CTkFrame(bubble, fg_color="transparent")
        button_row.pack(pady=10)
        ctk.CTkButton(
            button_row,
            text="Rename PDF" if session.get("rename_only") else "Export PDFs",
            command=(lambda: self.rename_only_files_now()) if session.get("rename_only")
            else (lambda: self.export_session(session))
        ).pack(side="left", padx=10)
        ctk.CTkButton(
            button_row, text="Reset Form", fg_color="#cc4b4b", hover_color="#aa2b2b",
            command=self.reset_ui
        ).pack(side="left", padx=10)
        ctk.CTkButton(button_row, text="Show Keybinds", command=self.open_keybind_overlay).pack(side="left", padx=10)

        self._apply_font_size()

        # Rendering/rebuilding a workspace can leave CustomTkinter's internal
        # scroll canvas at its previous position. That makes the first Part look
        # clipped even when the tile geometry is correct. Always start a newly
        # rendered Parts pane at the top.
        def _scroll_parts_to_top(frame=form_frame):
            try:
                canvas = getattr(frame, "_parent_canvas", None)
                if canvas is not None and canvas.winfo_exists():
                    canvas.yview_moveto(0.0)
                    canvas.xview_moveto(0.0)
            except (tk.TclError, AttributeError):
                pass

        self.after_idle(_scroll_parts_to_top)
        self.after(75, _scroll_parts_to_top)

    def jump_pdf_preview_to_page(self, session, page_index, part_index=None):
        # part_index is accepted for backward compatibility, but there is only one
        # static preview for the whole PDF session.
        frame = session.get("preview_frame")
        if frame is None:
            return
        try:
            if not frame.winfo_exists():
                return
            page_count = int(session.get("preview_page_count", len(session.get("reader", {}).pages) if session.get("reader") else 0))
            if page_count:
                page_index = max(0, min(int(page_index), page_count - 1))
            for widget in frame.winfo_children():
                widget.destroy()
            self.render_pdf_preview(session, frame, page_index=page_index)
            debug(f"Preview jumped to page {page_index + 1}", "debug")
        except (tk.TclError, ValueError, TypeError):
            return

    def jump_pdf_preview_to_entered_page(self, session, raw_value):
        try:
            page_number = int(str(raw_value).strip())
        except (TypeError, ValueError):
            messagebox.showwarning("Invalid Page", "Enter a valid page number.")
            return

        page_count = int(session.get("preview_page_count", 0) or 0)
        if page_count <= 0:
            return
        if page_number < 1 or page_number > page_count:
            messagebox.showwarning(
                "Invalid Page",
                f"Enter a page number from 1 to {page_count}."
            )
            return
        self.jump_pdf_preview_to_page(session, page_number - 1)

    def update_pdf_preview_page_in_frame(self, session, frame, offset):
        try:
            current = int(session.get("preview_page_index", getattr(frame, "_preview_page_index", 0)))
            self.jump_pdf_preview_to_page(session, current + offset)
        except Exception as error:
            debug(f"Failed to update preview page: {error}", "error")

    def render_pdf_preview(self, session, frame, page_index=0):
        doc = None
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

            # Resize to fit the actual preview element. Freeform previews can be
            # much smaller or larger than the legacy docked panel.
            try:
                frame.update_idletasks()
                frame_width = frame.winfo_width()
                frame_height = frame.winfo_height()
            except tk.TclError:
                frame_width, frame_height = 0, 0
            max_width = max(120, (frame_width - 24) if frame_width > 40 else 365)
            max_height = max(100, (frame_height - 175) if frame_height > 200 else 650)
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
            frame._preview_page_index = page_index

            # === Controls ===
            ctk.CTkLabel(
                frame, text="Preview",
                font=(self.font_family, self.font_size + 1, "bold")
            ).pack(pady=(10, 2))
            ctk.CTkLabel(
                frame,
                text=Path(session["path"]).name,
                text_color="#888888",
                wraplength=430,
                justify="center"
            ).pack(pady=(0, 4))

            control_frame = ctk.CTkFrame(frame, fg_color="transparent")
            control_frame.pack(pady=(10, 0))

            if page_index > 0:
                prev_btn = ctk.CTkButton(
                    control_frame, text="← Prev", width=80,
                    command=lambda f=frame: self.update_pdf_preview_page_in_frame(session, f, -1)
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
                    command=lambda f=frame: self.update_pdf_preview_page_in_frame(session, f, 1)
                )
                next_btn.pack(side="left", padx=5)

            # === Direct page jump ===
            jump_row = ctk.CTkFrame(frame, fg_color="transparent")
            jump_row.pack(pady=(7, 0))
            ctk.CTkLabel(jump_row, text="Page").pack(side="left", padx=(0, 5))
            page_jump_var = ctk.StringVar(value=str(page_index + 1))
            page_jump_entry = CTkEntry(jump_row, textvariable=page_jump_var, width=62, justify="center")
            page_jump_entry.pack(side="left")
            ctk.CTkLabel(jump_row, text=f"of {page_count}").pack(side="left", padx=5)
            ctk.CTkButton(
                jump_row, text="Go", width=48,
                command=lambda v=page_jump_var: self.jump_pdf_preview_to_entered_page(session, v.get())
            ).pack(side="left", padx=(3, 0))
            page_jump_entry.bind(
                "<Return>",
                lambda _e, v=page_jump_var: self.jump_pdf_preview_to_entered_page(session, v.get())
            )

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
            if doc is not None:
                try:
                    doc.close()
                except Exception:
                    pass
            debug(f"Failed to render PDF preview (page {page_index}): {e}", "debug")
            ctk.CTkLabel(frame, text="Unable to preview PDF").pack()
    def export_session(self, session):
        workspace_name = session.get("workspace", "Accounting")
        profile = self.get_workspace_profile(workspace_name)
        client_name = self.title_case(session["client_name_var"].get().strip())

        missing_required = []
        missing_optional_dates = []

        for part_number, entry in enumerate(session.get("entries", []), start=1):
            for field in profile.get("fields", []):
                key = field.get("key")
                variable = entry.get("field_vars", {}).get(key)
                if variable is None or not self.field_is_visible(entry, field):
                    continue

                try:
                    value = variable.get()
                except Exception:
                    value = ""

                is_blank = (not value) if isinstance(value, bool) else not str(value).strip()
                if field.get("required") and is_blank:
                    missing_required.append(f"Part {part_number}: {field.get('label', key)}")
                    continue

                if field.get("type") == "date" and is_blank and not field.get("required"):
                    missing_optional_dates.append(f"Part {part_number}: {field.get('label', key)}")

                if is_blank:
                    continue

                try:
                    if field.get("type") == "date":
                        self.format_date_for_field(value, field)
                    elif field.get("type") == "currency":
                        self.format_currency_value(value)
                except ValueError as error:
                    messagebox.showerror(
                        "Invalid Field Value",
                        f"Part {part_number} — {field.get('label', key)}:\n{error}\n\nYou entered: {value}"
                    )
                    return

        if missing_required:
            messagebox.showerror(
                "Required Fields Missing",
                "Please fill in the following required field(s) before exporting:\n\n" +
                "\n".join(f"• {item}" for item in missing_required)
            )
            return

        if missing_optional_dates:
            if not messagebox.askyesno(
                "Missing Date",
                "The following date field(s) are blank:\n\n" +
                "\n".join(f"• {item}" for item in missing_optional_dates) +
                "\n\nYou can still export; blank dates will be omitted from filenames. Continue?"
            ):
                return

        # Future-date warning remains a warning, not a blocker.  Check all visible
        # Date fields and stop at the first one that needs confirmation.
        if not self.settings.get("suppressFutureDateWarning", False):
            today = datetime.date.today()
            for part_number, entry in enumerate(session.get("entries", []), start=1):
                for field in profile.get("fields", []):
                    if field.get("type") != "date" or not self.field_is_visible(entry, field):
                        continue
                    variable = entry.get("field_vars", {}).get(field.get("key"))
                    if variable is None or not str(variable.get()).strip():
                        continue
                    try:
                        entered_date = self.parse_flexible_date(variable.get())
                    except ValueError:
                        continue
                    if entered_date > today:
                        debug(
                            f"Future date found in part {part_number}, field {field.get('key')}: {variable.get()}",
                            "debug"
                        )
                        self.check_future_date(
                            variable.get(),
                            callback_on_confirm=lambda: self._finalize_export(session)
                        )
                        return

        self._finalize_export(session)

    def get_workspace_export_values(self, session, client_name, entry):
        workspace_name = session.get("workspace", "Accounting")
        profile = self.get_workspace_profile(workspace_name)
        values = {
            "client": client_name,
            "workspace": workspace_name
        }

        for field in profile.get("fields", []):
            key = field.get("key")
            if not key:
                continue
            variable = entry.get("field_vars", {}).get(key)
            if variable is None or not self.field_is_visible(entry, field):
                values[key] = ""
                continue

            try:
                raw = variable.get()
            except Exception:
                raw = ""

            field_type = field.get("type", "text")

            if field_type in {"checkbox", "toggle", "bool"}:
                if key == "revoked":
                    processed = "Revoked" if bool(raw) else ""
                else:
                    processed = field.get("label", key.replace("_", " ").title()) if bool(raw) else ""
            else:
                processed = str(raw or "").strip()

                if key == "agency":
                    processed = self.get_agency(processed)

                # This shortcut is intentionally hardcoded as requested.  It only
                # replaces INV when it is a standalone word, never in "Inventory".
                if key == "description" and processed:
                    processed = re.sub(r"\binv\b", "Invoice", processed, flags=re.IGNORECASE)

                if field_type == "currency" and processed:
                    processed = self.format_currency_value(processed)
                elif field_type == "date" and processed:
                    processed = self.format_date_for_field(processed, field)

                if field.get("title_case") and processed:
                    processed = self.title_case(processed)

            values[key] = processed

        # Backward-compatible special tokens used by the permanent Accounting
        # workspace and old saved filename templates.
        values.setdefault("revoked", "")
        values.setdefault("agency", "")
        values.setdefault("description", "")
        values.setdefault("date", "")
        values.setdefault("matter_number", "")
        values.setdefault("document_type", "")
        values["agency_description"] = " ".join(
            part for part in (values.get("agency", ""), values.get("description", "")) if part
        ).strip()
        return values

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
        class SafeValues(dict):
            def __missing__(self, key):
                return ""

        format_values = SafeValues(values)
        check_number = str(format_values.get("check_number", "") or "").strip()
        if check_number:
            format_values["check_number"] = " " + check_number

        try:
            base_name = template.format_map(format_values)
        except (ValueError, AttributeError) as error:
            fallback = self.settings.get("workspaces", {}).get(workspace_name, {}).get(
                "filename_template", "{client}_{date}"
            )
            debug(f"Invalid {workspace_name} filename template '{template}': {error}; using default", "warning")
            try:
                base_name = fallback.format_map(format_values)
            except Exception:
                base_name = values.get("client", "Document")

        base_name = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", base_name)
        # Optional fields such as Check Number may be surrounded by literal spaces
        # in a visual filename template. If the field is blank, remove the orphaned
        # space immediately before an underscore separator ("ACH _Client" -> "ACH_Client").
        base_name = re.sub(r"\s+_", "_", base_name)
        base_name = re.sub(r"_{2,}", "_", base_name)
        base_name = re.sub(r"\s{2,}", " ", base_name)
        base_name = base_name.strip(" _-")
        base_name = base_name.rstrip(". ")

        reserved_names = {
            "CON", "PRN", "AUX", "NUL",
            *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10))
        }
        if base_name.upper() in reserved_names:
            base_name = "_" + base_name
        return base_name or "Document"

    def get_session_filename(self, session, entry):
        """Build a filename through the same path used by every export mode."""
        workspace_name = session.get("workspace", "Accounting")
        client_name = self.title_case(session["client_name_var"].get().strip())
        values = self.get_workspace_export_values(session, client_name, entry)
        template = self.settings.get("workspaces", {}).get(workspace_name, {}).get(
            "filename_template", WORKSPACES.get(workspace_name, {}).get(
                "default_filename_template", "{client}_{date}"
            )
        )
        return self._format_workspace_filename(template, values, workspace_name)

    def _finalize_export(self, session):
        debug("Finalizing export...", "debug")

        workspace_name = session.get("workspace", "Accounting")
        client_name = self.title_case(session["client_name_var"].get().strip())
        folder = self.settings.get("export_folder")

        if not folder:
            folder = filedialog.askdirectory(title="Select Export Folder")
            if not folder:
                return

        out_dir = (
            Path(folder) / client_name
            if self.make_client_folder_var.get() and client_name
            else Path(folder)
        )
        out_dir.mkdir(parents=True, exist_ok=True)

        log_lines = []
        session["last_exported_files"] = []
        filename_template = self.settings.get("workspaces", {}).get(workspace_name, {}).get(
            "filename_template", "{client}_{date}"
        )

        remove_blanks = self.settings.get("remove_blank_pages", True)
        fitz_doc = None
        if remove_blanks:
            try:
                fitz_doc = fitz.open(str(session["path"]))
            except Exception as error:
                debug(f"Could not open visual blank-page checker: {error}", "warning")

        for idx, entry in enumerate(session.get("entries", []), start=1):
            writer = PdfWriter()
            r = entry["range"]
            skipped = []

            for page_index in range(r["start"], r["end"] + 1):
                page = session["reader"].pages[page_index]
                fitz_page = None
                if fitz_doc is not None and page_index < fitz_doc.page_count:
                    try:
                        fitz_page = fitz_doc.load_page(page_index)
                    except Exception:
                        fitz_page = None
                if remove_blanks and self.is_blank_page(page, fitz_page=fitz_page):
                    skipped.append(page_index + 1)
                    continue
                writer.add_page(page)

            try:
                values = self.get_workspace_export_values(session, client_name, entry)
            except ValueError as error:
                messagebox.showerror("Invalid Field Value", f"Error in Part {idx}:\n{error}")
                return

            base_name = self.get_session_filename(session, entry)
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

            profile = self.get_workspace_profile(workspace_name)
            field_pairs = []
            for field in profile.get("fields", []):
                key = field.get("key")
                if not key or not self.field_is_visible(entry, field):
                    continue
                value = values.get(key, "")
                if value != "":
                    field_pairs.append(f"{field.get('label', key)}={value}")
            field_summary = "; ".join(field_pairs) if field_pairs else "None"

            log_lines.append(
                f"Workspace: {workspace_name} | Client: {client_name} | File: {fname} | "
                f"Pages: {r['start']+1}-{r['end']+1} | Skipped: {skipped if skipped else 'None'} | "
                f"Agency: {values.get('agency', '')} | Desc: {values.get('description', '')} | "
                f"Date: {values.get('date', '') or 'None'} | Revoked: {values.get('revoked', '') == 'Revoked'} | "
                f"Matter: {values.get('matter_number', '')} | Document Type: {values.get('document_type', '')} | "
                f"Fields: {field_summary}"
            )

        if fitz_doc is not None:
            try:
                fitz_doc.close()
            except Exception:
                pass

        self.last_exported_files = list(session["last_exported_files"])
        if self.settings.get("export_log_enabled", True):
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.append_log_lines([f"[{timestamp}] {line}\n" for line in log_lines])
            self.load_full_log()

        messagebox.showinfo(
            "Export Complete",
            f"Exported {len(session['last_exported_files'])} {workspace_name} file(s) to:\n{out_dir}"
        )
        debug(f"Exported {workspace_name} files to: {out_dir}", "debug")

        tab_name = next((name for name, current in self.pdf_sessions.items() if current is session), None)
        if tab_name:
            self._close_pdf_session(session)

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
            text="Open a PDF to Begin",
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
            doc = None
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
                if doc is not None:
                    try:
                        doc.close()
                    except Exception:
                        pass
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
            doc = None
            try:
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
            except Exception as error:
                debug(f"Failed to calculate preview zoom: {error}", "error")
            finally:
                if doc is not None:
                    try:
                        doc.close()
                    except Exception:
                        pass

        win.after(50, set_initial_zoom)  # Wait for layout before rendering

    # ─── Text Utilities ───
    def is_blank_page(self, page, fitz_page=None):
        """Return True only when a page is confidently blank.

        Text is checked first. For scanner-produced PDFs, a low-resolution
        grayscale render is inspected so image-only documents are never treated
        as blank merely because they have no OCR/text layer. The thresholds are
        intentionally conservative: uncertain pages are kept.
        """
        if fitz_page is not None:
            try:
                text = fitz_page.get_text("text") or ""
            except Exception:
                text = ""
        else:
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""

        compact_text = "".join(text.split())
        alphanumeric_count = len(re.findall(r"[A-Za-z0-9]", compact_text))
        if alphanumeric_count >= 4:
            return False

        # Preserve pages with annotations even if they have no extractable text.
        try:
            if page.get("/Annots"):
                return False
        except Exception:
            pass

        if fitz_page is None:
            # Without a visual rendering, only remove a page whose content stream
            # is genuinely empty. Anything uncertain is safer to preserve.
            try:
                contents = page.get_contents()
                if contents is None:
                    return True
                if isinstance(contents, list):
                    data = b"".join(item.get_data() for item in contents if item is not None)
                else:
                    data = contents.get_data()
                compact = re.sub(rb"\s+", b"", data or b"")
                return compact in {b"", b"qQ", b"qqQQ"}
            except Exception:
                return False

        try:
            # A small grayscale render is enough to detect ink while keeping
            # blank-page checking fast even for large batch scans.
            pix = fitz_page.get_pixmap(
                matrix=fitz.Matrix(0.35, 0.35),
                colorspace=fitz.csGRAY,
                alpha=False
            )
            image = Image.frombytes("L", (pix.width, pix.height), pix.samples)

            # Scanner shadows and feeder edges are common. Ignore a small margin
            # so those artifacts alone do not make an otherwise blank page nonblank.
            if image.width > 20 and image.height > 20:
                mx = max(2, int(image.width * 0.025))
                my = max(2, int(image.height * 0.025))
                image = image.crop((mx, my, image.width - mx, image.height - my))

            image.thumbnail((240, 320))
            histogram = image.histogram()
            total = max(1, sum(histogram))
            mean_gray = sum(level * count for level, count in enumerate(histogram)) / total

            cumulative = 0
            background_level = 255
            target = total * 0.90
            for level, count in enumerate(histogram):
                cumulative += count
                if cumulative >= target:
                    background_level = level
                    break

            light_cutoff = max(0, background_level - 12)
            dark_cutoff = max(0, background_level - 35)
            very_dark_cutoff = max(0, background_level - 70)
            light_ink = sum(histogram[:light_cutoff]) / total if light_cutoff else 0.0
            dark_ink = sum(histogram[:dark_cutoff]) / total if dark_cutoff else 0.0
            very_dark_ink = sum(histogram[:very_dark_cutoff]) / total if very_dark_cutoff else 0.0

            blank = (
                background_level >= 225
                and light_ink <= 0.012
                and dark_ink <= 0.003
                and very_dark_ink <= 0.001
            )
            debug(
                f"Blank-page visual check: mean={mean_gray:.2f}, background={background_level}, "
                f"light-ink={light_ink:.4%}, dark-ink={dark_ink:.4%}, "
                f"very-dark={very_dark_ink:.4%} -> {'blank' if blank else 'keep'}",
                "debug"
            )
            return blank
        except Exception as error:
            debug(f"Visual blank-page check failed; preserving page: {error}", "warning")
            return False
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

    def force_title_case_client_name(self, session):
        """Explicitly normalize pasted names without changing normal export rules."""
        current = session.get("client_name_var").get().strip()
        if current:
            session["client_name_var"].set(self.title_case(current.lower()))
        self.hide_client_suggestions()

    def get_output_client_folder_names(self):
        """Return client names from output folders and previous export history."""
        output_folder = str(self.settings.get("export_folder", "") or "").strip()
        names = []
        seen = set()
        if output_folder:
            root = Path(output_folder)
            try:
                folders = sorted(
                    (item for item in root.iterdir() if item.is_dir()),
                    key=lambda item: item.name.casefold()
                ) if root.is_dir() else []
            except (OSError, PermissionError):
                folders = []
            for folder in folders:
                name = folder.name.strip()
                if name and not name.startswith(".") and name.casefold() != "quick split files":
                    if name.casefold() not in seen:
                        seen.add(name.casefold())
                        names.append(name)

        # Keep names available after the output folder changes, and when client
        # folders were not created for an earlier export.
        try:
            if LOG_FILE.exists():
                for line in LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
                    match = re.search(r"\bClient:\s*([^|]+)", line, flags=re.IGNORECASE)
                    if match:
                        name = match.group(1).strip()
                        if name and name.casefold() not in seen:
                            seen.add(name.casefold())
                            names.append(name)
        except OSError as error:
            debug(f"Could not read client history: {error}", "warning")
        debug(f"Client autofill found {len(names)} remembered name(s)", "debug")
        return names

    def rank_client_folder_matches(self, query, names, limit=3):
        """Return exact consecutive matches: name prefix, word prefix, substring."""
        query = str(query or "").strip().casefold()
        if not query:
            return []

        def score(name):
            folded = name.casefold()
            words = re.findall(r"[a-z0-9]+", folded)
            if folded.startswith(query):
                match_level = 0
            elif any(word.startswith(query) for word in words):
                match_level = 1
            else:
                match_level = 2
            return (match_level, folded.find(query), folded)

        exact_matches = [name for name in names if query in name.casefold()]
        return sorted(exact_matches, key=score)[:max(1, int(limit))]

    def hide_client_suggestions(self):
        listbox = getattr(self, "client_suggestion_listbox", None)
        if listbox is not None:
            try:
                listbox.pack_forget()
                listbox.delete(0, "end")
            except tk.TclError:
                pass
        self.client_suggestion_listbox = None

    def move_client_suggestion(self, direction):
        listbox = getattr(self, "client_suggestion_listbox", None)
        if listbox is None:
            return None
        try:
            size = listbox.size()
            if size <= 0:
                return None
            current = listbox.curselection()
            index = current[0] if current else 0
            index = max(0, min(size - 1, index + int(direction)))
            listbox.selection_clear(0, "end")
            listbox.selection_set(index)
            listbox.activate(index)
            listbox.see(index)
            return "break"
        except tk.TclError:
            return None

    def accept_client_suggestion(self, session, entry):
        listbox = getattr(self, "client_suggestion_listbox", None)
        if listbox is None:
            return None
        try:
            picked = listbox.curselection()
            index = picked[0] if picked else 0
            if listbox.size() > 0:
                session["client_name_var"].set(listbox.get(index))
                entry.icursor("end")
                self.hide_client_suggestions()
                return "break"
        except tk.TclError:
            self.hide_client_suggestions()
        return None

    def show_client_suggestions(self, session, entry):
        self.hide_client_suggestions()
        query = session["client_name_var"].get().strip().casefold()
        if not query:
            return
        matches = self.rank_client_folder_matches(
            query,
            self.get_output_client_folder_names(),
            limit=3
        )
        debug(f"Client autofill query '{query}' matched: {matches}", "debug")
        if not matches:
            return

        listbox = session.get("client_suggestion_listbox")
        if listbox is None:
            debug("Client autofill could not display: inline listbox is unavailable", "warning")
            return
        try:
            if not listbox.winfo_exists():
                return
            listbox.delete(0, "end")
            listbox.configure(height=len(matches))
        except tk.TclError:
            return
        for name in matches:
            listbox.insert("end", name)
        listbox.selection_set(0)
        listbox.activate(0)
        listbox.pack(fill="x", pady=(2, 0))
        listbox.lift()
        self.client_suggestion_listbox = listbox

    # ─── Keybinds ───
    def focus_search(self):
        debug("Focusing search bar", "debug")
        self.notebook.set("Logs")
        self.search_entry.focus_set()

    def get_active_session(self):
        session = getattr(self, "active_pdf_session", None)
        if session is not None and any(current is session for current in self.pdf_sessions.values()):
            return session
        return None

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
        # PDF navigation is handled by the document sidebar in 1.10.1.
        # Do not bind the legacy hidden tab buttons; those handlers can race
        # sidebar selection and were the source of the selection crash.
        if hasattr(self, "pdf_document_tree"):
            return
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
                session = self.pdf_sessions.get(base_name)
                if session is not None:
                    self._close_pdf_session(session)
                else:
                    self.pdf_tabview.delete(tab_label)
            else:
                debug(f"[DEBUG] User canceled close for '{tab_label}'")
        else:
            debug(f"Click not in ✖ zone for '{tab_label}' — tab selected", "debug")
            try:
                self.pdf_tabview.set(tab_label)
                base_name = tab_label.replace(" ✖", "")
                session = self.pdf_sessions.get(base_name)
                if session is not None:
                    self._activate_pdf_session(session)
            except Exception as error:
                debug(f"Could not activate selected PDF tab '{tab_label}': {error}", "error")
    def _on_tab_right_click(self, tab_name):
        if tab_name == "+":
            return

        confirm = messagebox.askyesno("Close Tab", f"Close '{tab_name}'?")
        if confirm:
            session = self.pdf_sessions.get(tab_name)
            if session is not None:
                self._close_pdf_session(session)
            else:
                self.pdf_tabview.delete(tab_name)
    def close_current_tab(self):
        tab_label = self.pdf_tabview.get()
        if tab_label in {"+", "➕ New PDF"}:
            return

        base_name = tab_label.replace(" ✖", "")
        confirm = messagebox.askyesno("Close Tab", f"Close '{base_name}'?")
        if not confirm:
            return

        session = self.pdf_sessions.get(base_name)
        if session is not None:
            self._close_pdf_session(session)
        else:
            try:
                self.pdf_tabview.delete(tab_label)
            except tk.TclError:
                pass
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

        toolbar = ctk.CTkFrame(self.debug_console_window, fg_color="transparent")
        toolbar.pack(fill="x", padx=8, pady=8)

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

        test_button = ctk.CTkButton(
            toolbar,
            text="Run Edge/Stress Tests",
            width=170,
            command=lambda: self.run_dev_stress_tests(text_area)
        )
        test_button.pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            toolbar,
            text="Clear Debug Window",
            width=150,
            command=lambda: self.clear_debug_console(text_area)
        ).pack(side="left")
        ctk.CTkButton(
            toolbar,
            text="Open Crash Log",
            width=125,
            command=self.open_crash_log
        ).pack(side="left", padx=(8, 0))

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

    def open_crash_log(self):
        """Open the persisted crash diagnostics in the system text editor."""
        if not CRASH_FILE.exists():
            messagebox.showinfo("Crash Log", "No crash log has been recorded yet.")
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(CRASH_FILE))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(CRASH_FILE)])
            else:
                subprocess.Popen(["xdg-open", str(CRASH_FILE)])
        except Exception as error:
            _write_handled_exception("Open crash log", error)
            messagebox.showerror("Crash Log", f"Could not open the crash log:\n{CRASH_FILE}")

    def clear_debug_console(self, text_area):
        try:
            text_area.configure(state="normal")
            text_area.delete("1.0", "end")
            text_area.configure(state="disabled")
        except tk.TclError:
            pass

    def _write_dev_test_result(self, text_area, message, tag=None):
        try:
            text_area.configure(state="normal")
            text_area.insert("end", message + "\n", tag or "info")
            text_area.see("end")
            text_area.configure(state="disabled")
        except tk.TclError:
            pass

    def run_dev_stress_tests(self, text_area):
        """Run isolated PDF edge cases and a larger detection stress test."""
        self._write_dev_test_result(text_area, "", "info")
        self._write_dev_test_result(text_area, "=== CleanCutPDF Edge/Stress Tests ===", "info")
        self._write_dev_test_result(text_area, "Temporary test files will be deleted automatically.", "info")
        started = time.perf_counter()
        passed = 0
        failed = 0

        def check(label, condition, detail=""):
            nonlocal passed, failed
            if condition:
                passed += 1
                self._write_dev_test_result(text_area, f"PASS  {label}", "info")
            else:
                failed += 1
                suffix = f" — {detail}" if detail else ""
                self._write_dev_test_result(text_area, f"FAIL  {label}{suffix}", "error")

        try:
            with tempfile.TemporaryDirectory(prefix="CleanCutPDFStress-") as temp_name:
                temp_dir = Path(temp_name)

                # Text-marker edge cases: valid variants must split, while near
                # matches such as TEST B and SPLIT THERE must not.
                edge_path = temp_dir / "edge cases café résumé.pdf"
                edge_doc = fitz.open()
                edge_text = [
                    "Normal document page",
                    "SPLIT HERE",
                    "This page must stay with the next document",
                    "SPLIT-HERE",
                    "TEST B should not be treated as a marker",
                    "SPLIT THERE should not be treated as a marker",
                    "SPLIT\nHERE",
                    "Final document page"
                ]
                for page_text in edge_text:
                    page = edge_doc.new_page()
                    page.insert_text((72, 100), page_text, fontsize=18)
                edge_doc.save(str(edge_path))
                edge_doc.close()

                edge_reader = PdfReader(str(edge_path))
                edge_ranges = self.detect_split_ranges_from_reader(edge_reader, source_path=edge_path)
                expected_edge = [
                    {"start": 0, "end": 0},
                    {"start": 2, "end": 2},
                    {"start": 4, "end": 5},
                    {"start": 7, "end": 7}
                ]
                check("marker variants and false positives", edge_ranges == expected_edge, str(edge_ranges))

                # A PDF without separators must remain one complete part.
                single_path = temp_dir / "no markers.pdf"
                single_doc = fitz.open()
                single_doc.new_page().insert_text((72, 100), "No separator here", fontsize=18)
                single_doc.save(str(single_path))
                single_doc.close()
                single_ranges = self.detect_split_ranges_from_reader(
                    PdfReader(str(single_path)), source_path=single_path
                )
                check("no-marker PDF remains one part", single_ranges == [{"start": 0, "end": 0}], str(single_ranges))

                # Image-only colored separator pages model the real-world PDF
                # supplied during testing. The marker text is rasterized into a
                # PNG before insertion, so there is intentionally no text layer.
                visual_path = temp_dir / "image-only split markers.pdf"
                marker_source = fitz.open()
                marker_page = marker_source.new_page()
                marker_page.insert_text((72, 420), "SPLIT HERE", fontsize=72)
                marker_pix = marker_page.get_pixmap(matrix=fitz.Matrix(1.0, 1.0), alpha=False)
                marker_png = marker_pix.tobytes("png")
                marker_source.close()

                visual_doc = fitz.open()
                for page_index in range(8):
                    page = visual_doc.new_page()
                    if page_index in {2, 5}:
                        page.insert_image(page.rect, stream=marker_png)
                    else:
                        page.insert_text((72, 100), f"Image-only test page {page_index + 1}", fontsize=18)
                visual_doc.save(str(visual_path))
                visual_doc.close()
                visual_ranges = self.detect_split_ranges_from_reader(
                    PdfReader(str(visual_path)), source_path=visual_path
                )
                expected_visual = [
                    {"start": 0, "end": 1},
                    {"start": 3, "end": 4},
                    {"start": 6, "end": 7}
                ]
                check("image-only visual split markers", visual_ranges == expected_visual, str(visual_ranges))

                # Stress detection with many pages. This exercises the same path
                # Sydney uses when opening a large scanned batch.
                stress_path = temp_dir / "stress-500-pages.pdf"
                stress_doc = fitz.open()
                stress_marker_pages = set()
                for page_index in range(500):
                    page = stress_doc.new_page()
                    if page_index in {99, 199, 299, 399}:
                        page.insert_text((72, 100), "SPLIT HERE", fontsize=18)
                        stress_marker_pages.add(page_index)
                    else:
                        page.insert_text((72, 100), f"Stress page {page_index + 1}", fontsize=10)
                stress_doc.save(str(stress_path))
                stress_doc.close()

                stress_start = time.perf_counter()
                stress_ranges = self.detect_split_ranges_from_reader(
                    PdfReader(str(stress_path)), source_path=stress_path
                )
                stress_seconds = time.perf_counter() - stress_start
                expected_count = len(stress_marker_pages) + 1
                check(
                    "500-page split detection completes correctly",
                    len(stress_ranges) == expected_count,
                    f"got {len(stress_ranges)}, expected {expected_count}"
                )
                check("500-page stress run finishes under 30 seconds", stress_seconds < 30, f"{stress_seconds:.2f}s")
                self._write_dev_test_result(text_area, f"Stress timing: {stress_seconds:.2f} seconds", "info")

                # Filename collision behavior must produce a unique output path.
                collision_dir = temp_dir / "collision"
                collision_dir.mkdir()
                (collision_dir / "Document.pdf").write_bytes(b"existing")
                unique_path = self.get_unique_output_path(collision_dir, "Document")
                check("filename collision gets a unique path", unique_path.name == "Document_2.pdf", str(unique_path))

        except Exception as error:
            failed += 1
            self._write_dev_test_result(text_area, f"FAIL  test runner crashed — {error}", "error")
            debug(f"Developer stress tests failed: {error}", "error")

        elapsed = time.perf_counter() - started
        summary_tag = "info" if failed == 0 else "error"
        self._write_dev_test_result(
            text_area,
            f"=== Results: {passed} passed, {failed} failed in {elapsed:.2f} seconds ===",
            summary_tag
        )
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
            ("Split & Rename Workspace",
             "This is the main document workspace. PDFs are organized in the sidebar, while the selected PDF opens in the editor on the right.",
             "Split & Rename"),
            ("Documents Sidebar",
             "Inbox is always selected when CleanCutPDF starts. Your saved folders and documents stay in the sidebar, but no PDF editor opens automatically.",
             "Split & Rename"),
            ("Opening and Organizing PDFs",
             "Click Open PDFs or drag PDFs into the app. New files go into the currently selected folder. Use New Folder to create your own organization.",
             "Split & Rename"),
            ("Selecting Multiple PDFs",
             "Click one PDF to open it. Use Ctrl-click or Shift-click to select multiple PDFs. The sidebar shows how many documents are selected.",
             "Split & Rename"),
            ("Bulk Workspace Changes",
             "After selecting multiple PDFs, use Change Workspace for Selected to apply Accounting, Deposits, Misc., or another workspace to all of them at once.",
             "Split & Rename"),
            ("Moving Documents",
             "Select one or more PDFs and use Move Selected to Folder to organize them without moving the original files on your computer.",
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
             "Choose the default export folder and export logging here.",
             "Settings", lambda: self._show_settings_section("Export")),
            ("Behavior Settings",
             "Control blank-page removal, date warnings, session restore, and update behavior here.",
             "Settings", lambda: self._show_settings_section("Behavior")),
            ("Workspaces Settings",
             "Create, rename, or delete workspaces here. Accounting is permanent. Filename formats are also configured per workspace.",
             "Settings", lambda: self._show_settings_section("Workspaces")),
            ("Custom Fields Settings",
             "Create reusable fields, edit their types and rules, assign them to workspaces, and drag them into the order you want.",
             "Settings", lambda: self._show_settings_section("Custom Fields")),
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
        # These steps teach actions that must be performed in the main window.
        # A modal tutorial dialog would intercept those clicks and make the
        # tutorial appear stuck at the sidebar steps.
        interactive_steps = {4, 5, 6}

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
            is_interactive = index in interactive_steps
            debug(
                f"Tutorial step {index + 1}/{len(steps)}: {title}"
                f" ({'interactive' if is_interactive else 'informational'})",
                "debug"
            )

            try:
                self.notebook.set(tab)
                if callback:
                    callback()
            except Exception as error:
                debug(f"Tutorial navigation warning: {error}", "warning")

            window = state.get("window")
            if window and window.winfo_exists():
                try:
                    window.grab_release()
                except tk.TclError:
                    pass
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
            tutorial_width = 560
            # Step 6 has a longer wrapped explanation; leave enough room for
            # the message and the full button row at normal Windows scaling.
            tutorial_height = 420 if is_interactive else 285
            window.geometry(f"{tutorial_width}x{tutorial_height}")
            window.resizable(False, False)
            window.transient(self)
            window.protocol("WM_DELETE_WINDOW", cancel_tutorial)
            if is_interactive:
                msg = f"{msg}\n\nTry this in the main window, then click Next."

            self.update_idletasks()
            x = self.winfo_rootx() + max(0, (self.winfo_width() - tutorial_width) // 2)
            y = self.winfo_rooty() + max(0, (self.winfo_height() - tutorial_height) // 2)
            window.geometry(f"{tutorial_width}x{tutorial_height}+{x}+{y}")

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

            if not is_interactive:
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
                # Never write license credentials to the debug log.
                debug("Loaded cached license key", "debug")
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
        # The hash is also sensitive enough to omit from user-facing logs.
        debug("License key hash generated", "debug")

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
            self._set_main_window_title()
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
