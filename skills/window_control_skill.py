from __future__ import annotations

import ctypes
import subprocess
from typing import Any

import pygetwindow as gw


def _find_window(app: str) -> Any | None:
    app_lower = app.lower()
    all_windows = gw.getAllWindows()

    # Búsqueda exacta primero
    for win in all_windows:
        if app_lower in win.title.lower():
            return win
    return None


def minimize_window(app: str) -> str:
    try:
        win = _find_window(app)
        if win:
            win.minimize()
            return f"Minimicé {app}."
        return f"No encontré ventana de {app}."
    except Exception as e:
        return f"Error: {str(e)}"


def maximize_window(app: str) -> str:
    try:
        win = _find_window(app)
        if win:
            win.maximize()
            return f"Maximicé {app}."
        return f"No encontré ventana de {app}."
    except Exception as e:
        return f"Error: {str(e)}"


def close_window(app: str) -> str:
    try:
        win = _find_window(app)
        if win:
            win.close()
            return f"Cerré {app}."
        # Intentar cerrar por proceso
        subprocess.run(["taskkill", "/f", "/im", f"{app}.exe"], capture_output=True)
        return f"Cerré {app}."
    except Exception as e:
        return f"Error: {str(e)}"


def focus_window(app: str) -> str:
    try:
        win = _find_window(app)
        if win:
            win.activate()
            return f"Enfoqué {app}."
        return f"No encontré ventana de {app}."
    except Exception as e:
        return f"Error: {str(e)}"


def move_window(app: str, position: str = "center") -> str:
    try:
        user32 = ctypes.windll.user32
        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)

        win = _find_window(app)
        if not win:
            return f"No encontré ventana de {app}."

        w = screen_w // 2
        h = screen_h

        positions = {
            "left": (0, 0, w, h),
            "right": (w, 0, w, h),
            "center": (screen_w // 4, screen_h // 8, screen_w // 2, screen_h * 3 // 4),
            "fullscreen": (0, 0, screen_w, screen_h),
        }

        coords = positions.get(str(position).lower(), positions["center"])
        win.moveTo(coords[0], coords[1])
        win.resizeTo(coords[2], coords[3])
        return f"Moví {app} a {position}."
    except Exception as e:
        return f"Error: {str(e)}"


def list_windows() -> str:
    try:
        windows = [w.title for w in gw.getAllWindows() if w.title.strip()]
        if not windows:
            return "No hay ventanas abiertas."
        return f"Ventanas abiertas ({len(windows)}):\n" + "\n".join(f"- {w}" for w in windows[:15])
    except Exception as e:
        return f"Error: {str(e)}"
