import argparse
import ctypes
import datetime
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request
from pathlib import Path

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
# ─────────────────────────────────────────────
# CleanCutPDF Updater
# ─────────────────────────────────────────────

VERSION_INFO_URL = 'https://raw.githubusercontent.com/shhmethan/CleanCutPDF/master1/version.json'

# ─────────────────────────────────────────────
# USER DATA
# ─────────────────────────────────────────────

USER_DATA_DIR = Path.home() / '.cleancutpdf'
SETTINGS_FILE = USER_DATA_DIR / 'settings.json'
LOG_FILE = USER_DATA_DIR / 'full.log'
PINK_LIGHT = USER_DATA_DIR / 'pink_light.json'
PINK_DARK = USER_DATA_DIR / 'pink_dark.json'
DEFAULT_SETTINGS = {'font_family': 'Segoe UI', 'font_size': 12, 'theme': 'Light Blue'}


# ─────────────────────────────────────────────
# UPDATE LOGGING
# ─────────────────────────────────────────────

def write_update_log(message):
    try:
        USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(LOG_FILE, 'a', encoding='utf-8') as file:
            file.write(f'[{timestamp}] Update: {message}\n')
    except Exception as error:
        print(f'Could not write updater log: {error}')


# ─────────────────────────────────────────────
# VERSION FUNCTIONS
# ─────────────────────────────────────────────

def parse_version(version):
    version = version.strip().lower()
    if version.startswith('v'):
        version = version[1:]
    parts = version.split('.')
    numbers = []
    for part in parts:
        number = ''
        for char in part:
            if char.isdigit():
                number += char
            else:
                break
        numbers.append(int(number) if number else 0)
    while len(numbers) < 3:
        numbers.append(0)
    return tuple(numbers)

def is_newer_version(latest, current):
    return parse_version(latest) > parse_version(current)


# ─────────────────────────────────────────────
# SETTINGS
# ─────────────────────────────────────────────

def load_settings():
    settings = DEFAULT_SETTINGS.copy()
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as file:
                saved_settings = json.load(file)
            if isinstance(saved_settings, dict):
                settings.update(saved_settings)
    except Exception as error:
        print(f'Could not load settings: {error}')
    return settings


# ─────────────────────────────────────────────
# THEME
# ─────────────────────────────────────────────

def get_theme_config(theme_name):
    if theme_name == 'Light Pink' and PINK_LIGHT.exists():
        return {'mode': 'light', 'theme': str(PINK_LIGHT)}
    if theme_name == 'Dark Pink' and PINK_DARK.exists():
        return {'mode': 'dark', 'theme': str(PINK_DARK)}
    themes = {
        'Light Blue': {'mode': 'light', 'theme': 'blue'},
        'Dark Blue': {'mode': 'dark', 'theme': 'blue'},
        'Dark Green': {'mode': 'dark', 'theme': 'green'}
    }
    return themes.get(theme_name, {'mode': 'light', 'theme': 'blue'})


# ─────────────────────────────────────────────
# WAIT FOR CLEANCUTPDF TO CLOSE
# ─────────────────────────────────────────────

def wait_for_process(pid):
    if not pid:
        return
    try:
        SYNCHRONIZE = 1048576
        INFINITE = 4294967295
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
        if handle:
            kernel32.WaitForSingleObject(handle, INFINITE)
            kernel32.CloseHandle(handle)
    except Exception as error:
        print(f'Could not wait for process: {error}')


# ─────────────────────────────────────────────
# SHA256
# ─────────────────────────────────────────────

def calculate_sha256(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as file:
        while True:
            chunk = file.read(1024 * 1024)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest()


# ─────────────────────────────────────────────
# MAIN UPDATER WINDOW
# ─────────────────────────────────────────────

class CleanCutPDFUpdater(ctk.CTk):

    def __init__(self, current_version, app_path=None, app_pid=None):
        self.settings = load_settings()
        self.font_family = self.settings.get('font_family', 'Segoe UI')
        self.font_size = int(self.settings.get('font_size', 12))
        self.theme_name = self.settings.get('theme', 'Light Blue')
        theme = get_theme_config(self.theme_name)
        ctk.set_appearance_mode(theme['mode'])
        ctk.set_default_color_theme(theme['theme'])
        super().__init__()
        self.current_version = current_version
        self.latest_version = None
        self.download_url = None
        self.release_notes = ''
        self.expected_sha256 = ''
        self.downloaded_file = None
        self.update_stage = 'idle'
        self.app_path = Path(app_path) if app_path else None
        self.app_pid = app_pid
        self.title('CleanCutPDF Updater')
        self.window_width = 620
        self.window_height = 510
        self.geometry(f'{self.window_width}x{self.window_height}')
        self.resizable(False, False)
        self.center_window()
        self.build_ui()
        write_update_log(f'Updater opened | Current: {self.current_version}')
        self.after(500, self.check_for_updates)


    # ─────────────────────────────────────────
    # CENTER WINDOW
    # ─────────────────────────────────────────

    def center_window(self):
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = int((screen_width - self.window_width) / 2)
        y = int((screen_height - self.window_height) / 2)
        self.geometry(f'{self.window_width}x{self.window_height}+{x}+{y}')


    # ─────────────────────────────────────────
    # BUILD UI
    # ─────────────────────────────────────────

    def build_ui(self):
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill='both', expand=True, padx=22, pady=22)
        # ─── TITLE ───
        self.brand_label = ctk.CTkLabel(
            self.main_frame,
            text='CleanCutPDF',
            font=(self.font_family, self.font_size + 14, 'bold')
        )
        self.brand_label.pack(pady=(26, 2))
        self.updater_label = ctk.CTkLabel(self.main_frame, text='Updater', font=(self.font_family, self.font_size + 4))
        self.updater_label.pack(pady=(0, 22))

        # ─── VERSION BOX ───
        self.version_frame = ctk.CTkFrame(self.main_frame)
        self.version_frame.pack(fill='x', padx=45, pady=(0, 18))
        self.current_version_label = ctk.CTkLabel(
            self.version_frame,
            text=f'Current Version:   {self.current_version}',
            font=(self.font_family, self.font_size),
            anchor='w'
        )
        self.current_version_label.pack(fill='x', padx=18, pady=(15, 5))
        self.latest_version_label = ctk.CTkLabel(
            self.version_frame,
            text='Latest Version:     Checking...',
            font=(self.font_family, self.font_size),
            anchor='w'
        )
        self.latest_version_label.pack(fill='x', padx=18, pady=(5, 15))

        # ─── STATUS ───
        self.status_label = ctk.CTkLabel(
            self.main_frame,
            text='Checking for updates...',
            font=(self.font_family, self.font_size),
            wraplength=500
        )
        self.status_label.pack(pady=(4, 12))

        # ─── CUSTOM PROGRESS BAR ───
        self.progress_container = ctk.CTkFrame(self.main_frame, width=470, height=16, corner_radius=8)
        self.progress_container.pack(pady=(5, 6))
        self.progress_container.pack_propagate(False)
        self.progress_fill = ctk.CTkFrame(self.progress_container, width=1, height=16, corner_radius=8)
        self.progress_fill.place(x=0, y=0)
        self.percent_label = ctk.CTkLabel(
            self.main_frame,
            text='',
            font=(self.font_family, max(10, self.font_size - 1))
        )
        self.percent_label.pack(pady=(0, 8))

        # ─── AUTO LAUNCH ───
        self.auto_launch_var = ctk.BooleanVar(value=True)
        self.auto_launch_checkbox = ctk.CTkCheckBox(
            self.main_frame,
            text='Launch CleanCutPDF after update',
            variable=self.auto_launch_var,
            font=(self.font_family, self.font_size)
        )
        self.auto_launch_checkbox.pack(pady=(4, 12))

        # ─── MAIN UPDATE BUTTON ───
        self.update_button = ctk.CTkButton(
            self.main_frame,
            text='Checking...',
            width=180,
            height=38,
            state='disabled',
            font=(self.font_family, self.font_size),
            command=self.start_update
        )
        self.update_button.pack(pady=(5, 7))

        # ─── BUTTON ROW ───
        self.button_row = ctk.CTkFrame(self.main_frame, fg_color='transparent')
        self.button_row.pack(pady=(2, 10))
        self.notes_button = ctk.CTkButton(
            self.button_row,
            text='Release Notes',
            width=135,
            state='disabled',
            font=(self.font_family, self.font_size),
            command=self.show_release_notes
        )
        self.notes_button.pack(side='left', padx=6)
        self.close_button = ctk.CTkButton(
            self.button_row,
            text='Close',
            width=135,
            font=(self.font_family, self.font_size),
            command=self.destroy
        )
        self.close_button.pack(side='left', padx=6)

        # ─── FOOTER ───
        self.footer_label = ctk.CTkLabel(
            self.main_frame,
            text='CleanCutPDF Update Service',
            font=(self.font_family, max(10, self.font_size - 2)),
            text_color=('gray45', 'gray65')
        )
        self.footer_label.pack(side='bottom', pady=(0, 10))


    # ─────────────────────────────────────────
    # PROGRESS
    # ─────────────────────────────────────────

    def set_progress(self, percent):
        percent = max(0, min(100, percent))
        total_width = 470
        fill_width = int(total_width * (percent / 100))
        if fill_width < 1:
            fill_width = 1
        self.progress_fill.configure(width=fill_width)
        self.percent_label.configure(text=f'{percent}%')


    # ─────────────────────────────────────────
    # CHECK FOR UPDATES
    # ─────────────────────────────────────────

    def check_for_updates(self):
        self.status_label.configure(text='Checking for updates...')
        self.update_button.configure(text='Checking...', state='disabled')
        write_update_log(f'Check started | Current: {self.current_version}')
        thread = threading.Thread(target=self.check_worker, daemon=True)
        thread.start()

    def check_worker(self):
        try:
            request = urllib.request.Request(VERSION_INFO_URL, headers={'User-Agent': 'CleanCutPDF-Updater'})
            with urllib.request.urlopen(request, timeout=15) as response:
                data = json.loads(response.read().decode('utf-8'))
            self.latest_version = str(data['version'])
            self.download_url = data.get('download_url')
            self.release_notes = data.get('notes', 'No release notes available.')
            self.expected_sha256 = data.get('sha256', '').strip().lower()
            self.after(0, self.finish_check)
        except Exception as error:
            write_update_log(f'Check FAILED | Error: {error}')
            self.after(0, lambda: self.show_check_error(str(error)))

    def finish_check(self):
        self.latest_version_label.configure(text=f'Latest Version:     {self.latest_version}')
        self.notes_button.configure(state='normal')
        if is_newer_version(self.latest_version, self.current_version):
            self.status_label.configure(text=f'CleanCutPDF {self.latest_version} is available.')
            self.update_button.configure(text='Update Now', state='normal')
            write_update_log(f'Available | Current: {self.current_version} | Latest: {self.latest_version}')
        else:
            self.status_label.configure(text='You already have the latest version of CleanCutPDF.')
            self.update_button.configure(text='Up to Date', state='disabled')
            write_update_log(f'Up to date | Version: {self.current_version}')

    def show_check_error(self, error):
        self.status_label.configure(text='Unable to check for updates.')
        self.update_button.configure(text='Try Again', state='normal', command=self.check_for_updates)
        messagebox.showerror('Update Check Failed', f'CleanCutPDF could not check for updates.\n\n{error}')


    # ─────────────────────────────────────────
    # START UPDATE
    # ─────────────────────────────────────────

    def start_update(self):
        if not self.download_url:
            messagebox.showerror('Update Error', 'No update download URL was provided.')
            return
        if not self.app_path:
            messagebox.showerror('Update Error', 'The updater was not given the CleanCutPDF application path.')
            return
        try:
            # ─── SAFETY: NEVER UPDATE THE UPDATER ───
            own_executable = Path(sys.executable).resolve()
            target_executable = self.app_path.resolve()
            if getattr(sys, 'frozen', False) and own_executable == target_executable:
                write_update_log('Blocked self-update attempt')
                messagebox.showerror('Update Error', 'The updater cannot replace itself.')
                return
        except Exception:
            pass
        self.update_button.configure(state='disabled')
        self.notes_button.configure(state='disabled')
        self.close_button.configure(state='disabled')
        self.auto_launch_checkbox.configure(state='disabled')
        self.update_stage = 'downloading'
        self.set_progress(0)
        self.status_label.configure(text=f'Downloading CleanCutPDF {self.latest_version}...')
        write_update_log(f'Download started | Version: {self.latest_version}')
        thread = threading.Thread(target=self.download_worker, daemon=True)
        thread.start()


    # ─────────────────────────────────────────
    # DOWNLOAD
    # ─────────────────────────────────────────

    def download_worker(self):
        try:
            temp_dir = Path(tempfile.gettempdir()) / 'CleanCutPDFUpdate'
            temp_dir.mkdir(parents=True, exist_ok=True)
            downloaded_file = temp_dir / 'CleanCutPDF_new.exe'
            request = urllib.request.Request(self.download_url, headers={'User-Agent': 'CleanCutPDF-Updater'})
            with urllib.request.urlopen(request, timeout=30) as response:
                total_size = response.headers.get('Content-Length')
                if total_size:
                    total_size = int(total_size)
                downloaded = 0
                with open(downloaded_file, 'wb') as output:
                    while True:
                        chunk = response.read(1024 * 256)
                        if not chunk:
                            break
                        output.write(chunk)
                        downloaded += len(chunk)
                        if total_size:
                            percent = int(downloaded / total_size * 100)
                            self.after(0, lambda p=percent: self.set_progress(p))
            self.downloaded_file = downloaded_file
            write_update_log(f'Download complete | Version: {self.latest_version}')
            # ─── SHA256 VERIFICATION ───
            if self.expected_sha256:
                self.after(0, lambda: self.status_label.configure(text='Verifying update...'))
                write_update_log(f'Verification started | Version: {self.latest_version}')
                actual_hash = calculate_sha256(downloaded_file)
                if actual_hash.lower() != self.expected_sha256:
                    write_update_log(f'Verification FAILED | Version: {self.latest_version}')
                    raise ValueError('The downloaded update failed SHA256 verification.')
                write_update_log(f'Verification successful | Version: {self.latest_version}')
            self.after(0, self.prepare_install)
        except Exception as error:
            write_update_log(f'Download FAILED | Version: {self.latest_version} | Error: {error}')
            self.after(0, lambda: self.show_install_error(str(error)))


    # ─────────────────────────────────────────
    # PREPARE INSTALL
    # ─────────────────────────────────────────

    def prepare_install(self):
        self.set_progress(100)
        self.status_label.configure(text='Download complete. Installing update...')
        self.percent_label.configure(text='Preparing installation...')
        write_update_log(f'Install started | From: {self.current_version} | To: {self.latest_version}')
        thread = threading.Thread(target=self.install_worker, daemon=True)
        thread.start()


    # ─────────────────────────────────────────
    # INSTALL
    # ─────────────────────────────────────────

    def install_worker(self):
        backup_path = None
        try:
            # Wait for CleanCutPDF to close
            wait_for_process(self.app_pid)
            app_path = self.app_path
            if not app_path.parent.exists():
                raise FileNotFoundError('The CleanCutPDF installation folder does not exist.')
            # ─── BACKUP OLD EXE ───
            backup_path = app_path.parent / 'CleanCutPDF.old.exe'
            if backup_path.exists():
                backup_path.unlink()
            if app_path.exists():
                shutil.copy2(app_path, backup_path)
                write_update_log(f'Backup created | Path: {backup_path}')
            # ─── INSTALL NEW EXE ───
            shutil.copy2(self.downloaded_file, app_path)
            write_update_log(f'Installed | From: {self.current_version} | To: {self.latest_version}')
            self.after(0, self.finish_install)
        except Exception as error:
            write_update_log(
                f'Install FAILED | From: {self.current_version} | '
                f'To: {self.latest_version} | Error: {error}'
            )
            # ─── ATTEMPT ROLLBACK ───
            try:
                if backup_path and backup_path.exists():
                    shutil.copy2(backup_path, self.app_path)
                    write_update_log(f'Rollback successful | Restored: {self.current_version}')
            except Exception as rollback_error:
                write_update_log(f'Rollback FAILED | Error: {rollback_error}')
            self.after(0, lambda: self.show_install_error(str(error)))


    # ─────────────────────────────────────────
    # UPDATE COMPLETE
    # ─────────────────────────────────────────

    def finish_install(self):
        self.set_progress(100)
        self.status_label.configure(text=f'CleanCutPDF {self.latest_version} was installed successfully!')
        self.percent_label.configure(text='Update complete')
        self.notes_button.configure(state='normal')
        self.close_button.configure(state='normal')
        write_update_log(f'Update complete | Version: {self.latest_version}')
        if self.auto_launch_var.get():
            self.update_button.configure(text='Launching...', state='disabled')
            self.status_label.configure(
                text=(
                    f'CleanCutPDF {self.latest_version} was installed successfully. '
                    'Launching CleanCutPDF...'
                )
            )
            write_update_log(f'Automatic launch requested | Version: {self.latest_version}')
            self.after(1000, self.launch_app)
        else:
            self.update_button.configure(text='Launch CleanCutPDF', state='normal', command=self.launch_app)
            write_update_log(f'Automatic launch disabled | Version: {self.latest_version}')


    # ─────────────────────────────────────────
    # UPDATE ERROR
    # ─────────────────────────────────────────

    def show_install_error(self, error):
        self.status_label.configure(text='Update failed.')
        self.percent_label.configure(text='')
        self.update_button.configure(text='Try Again', state='normal', command=self.start_update)
        self.close_button.configure(state='normal')
        self.notes_button.configure(state='normal')
        self.auto_launch_checkbox.configure(state='normal')
        messagebox.showerror('Update Failed', f'CleanCutPDF could not be updated.\n\n{error}')


    # ─────────────────────────────────────────
    # LAUNCH CLEANCUTPDF
    # ─────────────────────────────────────────

    def launch_app(self):
        try:
            if not self.app_path:
                raise FileNotFoundError('CleanCutPDF application path is missing.')
            if not self.app_path.exists():
                raise FileNotFoundError('CleanCutPDF.exe could not be found.')
            subprocess.Popen([str(self.app_path)], cwd=str(self.app_path.parent))
            write_update_log(f'CleanCutPDF launched | Version: {self.latest_version}')
            self.destroy()
        except Exception as error:
            write_update_log(f'Launch FAILED | Version: {self.latest_version} | Error: {error}')
            messagebox.showerror('Launch Failed', f'CleanCutPDF was updated, but could not be launched.\n\n{error}')
            self.update_button.configure(text='Launch CleanCutPDF', state='normal', command=self.launch_app)


    # ─────────────────────────────────────────
    # RELEASE NOTES
    # ─────────────────────────────────────────

    def show_release_notes(self):
        window = tk.Toplevel(self)
        bg_color = ctk.ThemeManager.theme.get("CTkFrame", {}).get("fg_color", "#f0f0f0")

        if isinstance(bg_color, (list, tuple)):
            bg_color = (
                bg_color[0]
                if ctk.get_appearance_mode() == "Light"
                else bg_color[1]
            )

        window.configure(bg=bg_color)
        window.title(f'CleanCutPDF {self.latest_version}')
        window_width = 500
        window_height = 350
        window.geometry(f'{window_width}x{window_height}')
        window.resizable(False, False)
        window.transient(self)
        window.grab_set()
        # ─── CENTER RELEASE NOTES ───
        window.update_idletasks()
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = int((screen_width - window_width) / 2)
        y = int((screen_height - window_height) / 2)
        window.geometry(f'{window_width}x{window_height}+{x}+{y}')
        title = ctk.CTkLabel(
            window,
            text=f'CleanCutPDF {self.latest_version}',
            font=(self.font_family, self.font_size + 6, 'bold')
        )
        title.pack(pady=(22, 5))
        subtitle = ctk.CTkLabel(window, text='Release Notes', font=(self.font_family, self.font_size + 2))
        subtitle.pack(pady=(0, 12))
        is_light = ctk.get_appearance_mode() == "Light"

        textbox = tk.Text(
            window,
            width=54,
            height=10,
            font=(self.font_family, self.font_size),
            wrap="word",
            bg="#ffffff" if is_light else "#1f1f1f",
            fg="#1e1e1e" if is_light else "#f2f2f2",
            insertbackground="#1e1e1e" if is_light else "#f2f2f2",
            relief="flat",
            borderwidth=0
        )

        textbox.pack(
            padx=20,
            pady=8
        )

        textbox.insert(
            "1.0",
            self.release_notes
        )

        textbox.configure(
            state="disabled"
        )
        close_button = ctk.CTkButton(
            window,
            text='Close',
            width=120,
            font=(self.font_family, self.font_size),
            command=window.destroy
        )
        close_button.pack(pady=(8, 15))


# ─────────────────────────────────────────────
# COMMAND LINE ARGUMENTS
# ─────────────────────────────────────────────

def get_arguments():
    parser = argparse.ArgumentParser(description='CleanCutPDF Updater')
    parser.add_argument('--current-version', default='Current Not Available', help='Currently installed CleanCutPDF version')
    parser.add_argument('--app', default=None, help='Path to CleanCutPDF.exe')
    parser.add_argument('--pid', type=int, default=None, help='Process ID of the running CleanCutPDF application')
    return parser.parse_args()

# ─────────────────────────────────────────────
# START
# ─────────────────────────────────────────────

if __name__ == '__main__':
    args = get_arguments()
    app = CleanCutPDFUpdater(current_version=args.current_version, app_path=args.app, app_pid=args.pid)
    app.mainloop()