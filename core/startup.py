from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
import winreg

APP_NAME: str = "TUTUS"
LMS: str = os.path.expanduser(r"~\.lmstudio\bin\lms.exe")
log = logging.getLogger("tutus.startup")


def get_app_path() -> str:
    python = sys.executable.replace("python.exe", "pythonw.exe")
    main = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "main.py")
    return f'"{python}" "{os.path.normpath(main)}"'


def _run_lms(args: list[str]) -> subprocess.Popen[bytes] | None:
    if os.path.exists(LMS):
        return subprocess.Popen([LMS] + args, creationflags=subprocess.CREATE_NO_WINDOW)
    return None


def start_lmstudio() -> None:
    """Inicia el servidor de inferencia sin mostrar la ventana de LM Studio."""
    # Intentar arrancar el servidor directamente via lms (headless)
    if _run_lms(["server", "start"]):
        log.info("Servidor de inferencia iniciado (headless).")
        return

    # Fallback: lanzar la GUI minimizada
    lmstudio_path = os.path.join(os.environ["LOCALAPPDATA"], "Programs", "LM Studio", "LM Studio.exe")
    if not os.path.exists(lmstudio_path):
        log.warning("No encontré LM Studio en: %s", lmstudio_path)
        return

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 7  # SW_MINIMIZE (7) — solo icono en taskbar sin ventana

    subprocess.Popen(
        [lmstudio_path, "--headless"],
        startupinfo=startupinfo,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    log.info("LM Studio iniciado (minimizado).")

    time.sleep(5)
    _run_lms(["server", "start"])
    log.info("Servidor de inferencia iniciado.")


def enable_startup() -> None:
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY
    )
    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, get_app_path())
    winreg.CloseKey(key)
    log.info("TUTUS agregado al arranque de Windows.")


def disable_startup() -> None:
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY
        )
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        log.info("TUTUS removido del arranque.")
    except FileNotFoundError:
        log.warning("TUTUS no estaba en el arranque.")


def is_startup_enabled() -> bool:
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY
        )
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
