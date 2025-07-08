# ───── IMPORTS ─────
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
GLOBAL_LOG_FILE = USER_DATA_DIR / "full.log"
GLOBAL_KEYBINDS_FILE = USER_DATA_DIR / "keybinds.json"
GLOBAL_PINK_LIGHT = USER_DATA_DIR / "pink_light.json"
GLOBAL_PINK_DARK = USER_DATA_DIR / "pink_dark.json"

ACRONYMS = {"POA", "LLC", "INC", "LP", "LLP", "PLC", "DBA", "CPA", "PC", "PLLC", "LLLP"}
THEMES = {
    "Light Blue": {"mode": "light", "theme": "blue"},
    "Dark Blue": {"mode": "dark", "theme": "blue"},
    "Dark Green": {"mode": "dark", "theme": "green"},
    "Light Sydney": {"mode": "light", "theme": GLOBAL_PINK_LIGHT},
    "Dark Sydney": {"mode": "dark", "theme": GLOBAL_PINK_DARK}
}
FONTS = ["Segoe UI", "Consolas", "Courier New", "Arial", "Tahoma", "Verdana"]
DEFAULT_KEYBINDS = {
    "Open PDF": "ctrl+p",
    "Export PDFs": "ctrl+e",
    "Reset": "ctrl+r",
    "Quit": "ctrl+q",
    "Search Logs": "ctrl+f",
    "Undo Last Export": "ctrl+shift+z"
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
        if not GLOBAL_PINK_LIGHT.exists():
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

            with open(GLOBAL_PINK_LIGHT, "w", encoding="utf-8") as f:
                json.dump(pink_theme, f, indent=2)
def create_dark_pink_theme(self):
    if not GLOBAL_PINK_DARK.exists():
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

        with open(GLOBAL_PINK_DARK, "w", encoding="utf-8") as f:
            json.dump(dark_theme, f, indent=2)

# ───── MAIN APPLICATION ─────
class PDFSplitterApp(TkinterDnD.Tk):
    # ─── INITIALIZATION ───
    def __init__(self):
        super().__init__()
        self.title("CleanCutPDF Splitter")
        self.geometry("900x600")
        self.update_idletasks()
        self.state("zoomed")

        self.show_loading_overlay()

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
        try:
            with open(SETTINGS_FILE, "r") as f:
                self.settings = json.load(f)
                self.settings.setdefault("font_family", "Segoe UI")
        except (FileNotFoundError, json.JSONDecodeError):
            self.settings = {}
        try:
            with open(GLOBAL_KEYBINDS_FILE, "r") as f:
                file_keybinds = json.load(f)
                if not isinstance(file_keybinds, dict):
                    raise ValueError("Keybinds file must be a dictionary")
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            debug("[DEBUG] Generating default keybinds")
            file_keybinds = {}

        self.keybindings = {**DEFAULT_KEYBINDS, **file_keybinds}

        if self.keybindings != file_keybinds:
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

        bg_color = ctk.ThemeManager.theme["CTkFrame"]["fg_color"]
        if isinstance(bg_color, list):
            bg_color = bg_color[0] if ctk.get_appearance_mode() == "Light" else bg_color[1]

        self.dnd_frame = tk.Frame(wrapper, bg=bg_color, height=60)

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

        canvas_bg = ctk.ThemeManager.theme["CTkFrame"]["fg_color"]
        if isinstance(canvas_bg, list):
            canvas_bg = canvas_bg[0] if ctk.get_appearance_mode() == "Light" else canvas_bg[1]

        self.canvas = tk.Canvas(scroll_frame, borderwidth=0, highlightthickness=0, bg=canvas_bg)

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

        ctk.CTkLabel(self.settings_tab, text="Font Family").pack(pady=(20, 0))
        self.font_family_var = ctk.StringVar(value=self.font_family)
        font_menu = ctk.CTkOptionMenu(
            self.settings_tab,
            values=FONTS,
            variable=self.font_family_var,
            command=self.update_font_family
        )
        font_menu.pack(pady=5)
    def build_about_tab(self):
        text = (
            "CleanCutPDF Splitter v1.3\n\n"
            "CleanCutPDF is a responsive, customizable tool for cleanly and efficiently splitting PDF documents.\n\n"
            "New in Version 1.3:\n"
            "• Added Light Pink and Dark Pink themes\n"
            "• Fully customizable font size and font family\n"
            "• All keybindings are now editable in-app (double-click to change)\n"
            "• More helpful error messages for invalid date formats\n"
            "• Checkboxes, switches, and sliders now reflect theme colors\n"
            "• Improved tooltip spacing and UI layout polish\n\n"
            "Key Features:\n"
            "• Drag-and-drop PDF support\n"
            "• Auto-detects split markers (e.g., 'SPLIT HERE')\n"
            "• Metadata-driven filename generation (Agency, Description, Date)\n"
            "• Client name entry with responsive layout\n"
            "• Blank page removal (optional)\n"
            "• Custom export folder support\n"
            "• Export log with search, sort, and highlight\n"
            "• Undo Last Export (Ctrl+Shift+Z) with cleanup logging\n"
            "• Customizable keybindings (saved to keybinds.json)\n"
            "• Responsive font scaling and live theme switching\n"
            "Your preferences are saved to your user directory (.cleancutpdf).\n\n"
            "Designed by Ethan Brothers\n"
            "© 2025 — Version 1.3"
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
        if hasattr(self, "debug_console_text"):
            self.debug_console_text.configure(font=(self.font_family, self.font_size))

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
                with open(GLOBAL_LOG_FILE, "w", encoding="utf-8") as f:
                    f.write("")
                self.full_log_lines = []
                self.update_log_view()
                messagebox.showinfo("Log Cleared", "The export log has been successfully cleared.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear the log:\n{e}")

    # ─── PDF Load & Split ───
    def load_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if path:
            self.load_pdf_from_path(path)
    def load_pdf_from_path(self, path):
        debug(f"[DEBUG] Called load_pdf_from_path with path: {path}")
        self.show_loading_overlay()

        def finish_load():
            try:
                self.reader = PdfReader(path)
                self.pdf_path = Path(path)
                debug(f"[DEBUG] PDF loaded: {self.pdf_path.name}, Total pages: {len(self.reader.pages)}")

                self.ranges = self.detect_split_ranges()
                debug(f"[DEBUG] Ranges returned from detect_split_ranges: {self.ranges}")

                self.label_status.configure(text=f"Loaded: {self.pdf_path.name} ({len(self.ranges)} part(s))")

                if not self.client_name_visible:
                    client_outer = ctk.CTkFrame(self.parts_frame, width=700, height=40, fg_color="transparent")
                    client_outer.pack(pady=(10, 0))
                    client_outer.pack_propagate(False)

                    self.client_name_label = ctk.CTkLabel(client_outer, text="Client Name:")
                    self.client_name_label.pack(side="left", padx=(10, 10))

                    self.client_name_entry = ctk.CTkEntry(
                        client_outer,
                        textvariable=self.client_name_var,
                        placeholder_text="Enter Client Name"
                    )
                    self.client_name_entry.pack(side="left", fill="x", expand=True)
                    self.client_name_visible = True

                self.render_parts()
                self.canvas.yview_moveto(0)
                self.btn_process.configure(state="normal")
                self.btn_refresh.configure(state="normal")
                self._apply_font_size()

            except Exception as e:
                debug(f"[DEBUG] Exception occurred during load_pdf_from_path: {e}")
                messagebox.showerror("Failed to Load PDF", f"An error occurred:\n{str(e)}")

            self.hide_loading_overlay()  # 🔴 Hide overlay

        self.after(100, lambda: finish_load())
    def detect_split_ranges(self):
        debug("[DEBUG] Starting detect_split_ranges")
        split_pages = []
        for idx, page in enumerate(self.reader.pages):
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

        if start < len(self.reader.pages):
            ranges.append({"start": start, "end": len(self.reader.pages) - 1})
        if not ranges:
            ranges = [{"start": 0, "end": len(self.reader.pages) - 1}]

        debug(f"[DEBUG] Detected split ranges: {ranges}")
        return ranges
    def render_parts(self):
        debug("[DEBUG] Rendering parts...")
        for widget in self.parts_frame.winfo_children():
            if not (self.client_name_entry and widget == self.client_name_entry.master):
                widget.destroy()

        self.entries.clear()

        for idx, r in enumerate(self.ranges, start=1):
            debug(f"[DEBUG] Creating frame for Part {idx} — Pages {r['start']+1} to {r['end']+1}")
            frame = ctk.CTkFrame(self.parts_frame, width=640, fg_color="transparent")
            frame.pack(pady=10, anchor="center")

            ctk.CTkLabel(
                frame,
                text=f"Part {idx} — Pages {r['start']+1} to {r['end']+1}"
            ).grid(row=0, column=0, columnspan=2, pady=(0, 5), sticky="ew")

            # Variables
            revoked_var = ctk.BooleanVar()
            agency_var = ctk.StringVar()
            desc_var = ctk.StringVar(value="POA")
            date_var = ctk.StringVar()

            # Revoked switch
            ctk.CTkSwitch(frame, text="Revoked", variable=revoked_var).grid(row=1, column=0, sticky="w")

            # Agency row: Label + ℹ️ icon
            info_row = ctk.CTkFrame(frame, fg_color="transparent")
            info_row.grid(row=2, column=0, sticky="w", pady=(5, 0))

            ctk.CTkLabel(info_row, text="Agency Code:").pack(side="left")

            info_icon = ctk.CTkLabel(info_row, text="ℹ️", cursor="question_arrow")
            info_icon.pack(side="left", padx=(6, 0))  # Better spacing from label
            self.add_tooltip(info_icon, "Agency Codes:\n• i = IRS\n• f = FTB\n• e = EDD\n• c = CDTFA\n• b = BOE")

            # Entry for agency
            ctk.CTkEntry(frame, textvariable=agency_var).grid(row=2, column=1, padx=(0, 10), sticky="ew")

            # Description
            ctk.CTkLabel(frame, text="Description:").grid(row=3, column=0, sticky="w")
            ctk.CTkEntry(frame, textvariable=desc_var).grid(row=3, column=1)

            # Date
            ctk.CTkLabel(frame, text="Date (MMDDYY):").grid(row=4, column=0, sticky="w")
            ctk.CTkEntry(frame, textvariable=date_var).grid(row=4, column=1)

            # Store part entry data
            self.entries.append({
                "range": r,
                "revoked": revoked_var,
                "agency": agency_var,
                "description": desc_var,
                "date": date_var
            })

            # Autofill handlers
            agency_var.trace_add("write", self.make_autofill_handler("agency", agency_var, idx - 1))
            desc_var.trace_add("write", self.make_autofill_handler("description", desc_var, idx - 1))
            date_var.trace_add("write", self.make_autofill_handler("date", date_var, idx - 1))
            revoked_var.trace_add("write", self.make_autofill_handler("revoked", revoked_var, idx - 1))

            debug(f"[DEBUG] Finished Part {idx}")

        self._check_scrollbar_visibility()
        debug("[DEBUG] Finished rendering all parts")
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

        with open(GLOBAL_LOG_FILE, "a", encoding="utf-8") as f:
            for line in log_lines:
                f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {line}\n")

        self.last_exported_files.append(file_path)
        self.load_full_log()

        # Show post-export session summary
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
        def replacer(match):
            txt = match.group(0)
            clean = re.sub(r'[^A-Za-z]', '', txt)
            upper = clean.upper()

            if clean == "Inc" and txt.endswith("."):
                return "Inc."
            if upper in ACRONYMS and not txt.endswith("."):
                return upper
            if txt.isupper():
                return txt
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
        with open(GLOBAL_KEYBINDS_FILE, "w") as f:
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

        with open(GLOBAL_LOG_FILE, "a", encoding="utf-8") as f:
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

if __name__ == "__main__":
    app = PDFSplitterApp()
    app.mainloop()