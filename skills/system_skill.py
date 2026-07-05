from __future__ import annotations

import datetime
import difflib
import os
import subprocess
import urllib.parse
import webbrowser

APP_MAP = {
    "spotify": "spotify",
    "discord": "discord",
    "chrome": "chrome",
    "brave": r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    "firefox": "firefox",
    "edge": "msedge",
    "notepad": "notepad",
    "calculadora": "calc",
    "calculator": "calc",
    "explorador": "explorer",
    "explorer": "explorer",
    "explorador de archivos": "explorer",
    "paint": "mspaint",
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "vscode": "code",
    "vs code": "code",
    "terminal": "wt",
    "cmd": "cmd",
    "task manager": "taskmgr",
    "administrador de tareas": "taskmgr",
}


def open_app(app: str) -> str:
    try:
        app_lower = app.lower()

        if app_lower not in APP_MAP:
            matches = difflib.get_close_matches(app_lower, APP_MAP.keys(), n=1, cutoff=0.4)
            if matches:
                app_lower = matches[0]

        cmd = APP_MAP.get(app_lower, app_lower)
        if os.path.exists(cmd):
            subprocess.Popen([cmd])
        else:
            subprocess.Popen(["cmd", "/c", "start", "", cmd], shell=False)
        return f"Abriendo {app}"
    except Exception as e:
        return f"Error abriendo {app}: {str(e)}"


def get_weather(city: str = "Ciudad de Mexico") -> str:
    try:
        url = f"https://wttr.in/{urllib.parse.quote(city)}?lang=es"
        webbrowser.open(url)
        return f"Mostrando clima de {city}"
    except Exception as e:
        return f"Error: {str(e)}"


def get_time() -> str:
    now = datetime.datetime.now()
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    dia = dias[now.weekday()]
    mes = meses[now.month - 1]
    hora = now.strftime("%I:%M %p")
    return f"Son las {hora} del {dia} {now.day} de {mes} de {now.year}"
