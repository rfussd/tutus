from __future__ import annotations

import hashlib
import logging
import threading
import time
from collections.abc import Callable
from datetime import datetime

import mss
from PIL import Image

log = logging.getLogger("tutus.context_monitor")


_LAST_WINDOW: str = ""
_LAST_CLIPBOARD: str = ""
_LAST_SCREEN_HASH: str = ""
_COOLDOWN_TRACKER: dict[str, datetime] = {}
_monitor_thread: threading.Thread | None = None
_running: bool = False

on_window_change: Callable[[str, str], None] | None = None
on_clipboard_change: Callable[[str], None] | None = None
on_screen_change: Callable[[], None] | None = None
on_opportunity: Callable[[str, str], None] | None = None


def start_monitoring() -> None:
    global _monitor_thread, _running
    if _running:
        return
    _running = True
    _monitor_thread = threading.Thread(target=_monitor_loop, daemon=True)
    _monitor_thread.start()
    log.info("Monitoreo iniciado")


def stop_monitoring() -> None:
    global _running
    _running = False


def _get_foreground_window() -> tuple[str, str]:
    try:
        import win32gui
        import win32process

        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc_name = ""
        try:
            import psutil

            proc = psutil.Process(pid)
            proc_name = proc.name()
        except Exception as e:
            log.debug("proc name error: %s", e)
        return title, proc_name
    except Exception as e:
        log.debug("foreground window error: %s", e)
        return "", ""


def _get_clipboard_text() -> str:
    try:
        import win32clipboard

        win32clipboard.OpenClipboard()
        try:
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                return data[:500] if data else ""
        finally:
            win32clipboard.CloseClipboard()
    except Exception as e:
        log.debug("clipboard read error: %s", e)
    return ""


def _get_screen_hash() -> str:
    try:
        with mss.MSS() as sct:
            monitor = sct.monitors[1]
            thumbnail = sct.grab(monitor)
            img = Image.frombytes("RGB", thumbnail.size, thumbnail.bgra, "raw", "BGRX")
            img.thumbnail((160, 90))
            return hashlib.md5(img.tobytes()).hexdigest()
    except Exception as e:
        log.debug("screen hash error: %s", e)
        return ""


def _classify_window(title: str, proc_name: str) -> dict[str, str]:
    title_lower = title.lower()
    proc_lower = proc_name.lower()

    if proc_lower in ("code.exe", "cursor.exe", "windsurf.exe"):
        return {"context": "coding", "app": "editor", "detail": title}
    if proc_lower in ("chrome.exe", "edge.exe", "firefox.exe", "brave.exe"):
        return {"context": "browsing", "app": "browser", "detail": title}
    if "terminal" in title_lower or "cmd" in title_lower or "powershell" in title_lower:
        return {"context": "terminal", "app": "terminal", "detail": title}
    if "outlook" in title_lower or "mail" in title_lower:
        return {"context": "email", "app": "mail", "detail": title}
    if "explorer" in proc_lower:
        return {"context": "files", "app": "explorer", "detail": title}
    if "word" in title_lower or "excel" in title_lower or "powerpoint" in title_lower:
        return {"context": "office", "app": "office", "detail": title}
    if "spotify" in title_lower or "youtube music" in title_lower:
        return {"context": "music", "app": "music", "detail": title}

    return {"context": "other", "app": proc_name, "detail": title}


def _should_suggest(key: str, cooldown_min: int = 10) -> bool:
    now = datetime.now()
    if key in _COOLDOWN_TRACKER:
        elapsed = (now - _COOLDOWN_TRACKER[key]).total_seconds()
        if elapsed < cooldown_min * 60:
            return False
    _COOLDOWN_TRACKER[key] = now
    return True


def _detect_window_opportunity(title: str, proc_name: str, context: str, app: str) -> None:
    if not _should_suggest(f"window_{context}"):
        return

    if context == "coding":
        if on_opportunity:
            on_opportunity(
                "codigo",
                "Veo que estas programando. ¿Quieres que analice el archivo activo o te ayude con algo?",
            )

    elif context == "terminal":
        if on_opportunity:
            on_opportunity(
                "terminal",
                "Veo la terminal abierta. Si ves un error, dimelo y lo diagnostico.",
            )

    elif context == "browsing":
        if "gmail" in title.lower() or "mail" in title.lower() or "inbox" in title.lower():
            if _should_suggest("email_batch", 30):
                if on_opportunity:
                    on_opportunity(
                        "email",
                        "Estas viendo el correo. ¿Quieres que resuma tu bandeja de entrada?",
                    )

    elif context == "files":
        if _should_suggest("files", 20):
            if on_opportunity:
                on_opportunity(
                    "archivos",
                    "Estas en el explorador. ¿Quieres que indexe esta carpeta para poder buscarla después?",
                )

    elif context == "office":
        if on_opportunity:
            on_opportunity(
                "documento",
                "Veo que estas trabajando en un documento. ¿Necesitas ayuda con el contenido?",
            )

    elif context == "music":
        if _should_suggest("music", 60):
            if on_opportunity:
                on_opportunity(
                    "musica",
                    "¿Quieres que ponga música o controlo tu lista de reproducción?",
                )


def _detect_clipboard_opportunity(text: str) -> None:
    import re

    error_patterns = [
        r"traceback",
        r"error",
        r"exception",
        r"failed",
        r"syntaxerror",
        r"importerror",
        r"valueerror",
        r"typeerror",
        r"attributeerror",
        r"keyerror",
        r"filenotfounderror",
        r"modulenotfounderror",
        r"indexerror",
        r"runtimeerror",
    ]
    text_lower = text.lower()
    if any(re.search(p, text_lower) for p in error_patterns):
        if _should_suggest("clipboard_error", 5):
            if on_opportunity:
                on_opportunity(
                    "error",
                    "Parece que copiaste un error. ¿Quieres que lo analice y te diga como arreglarlo?",
                )

    if len(text) > 200 and _should_suggest("clipboard_long", 30):
        if on_opportunity:
            on_opportunity(
                "texto_largo",
                "Copiaste un texto largo. ¿Quieres que lo resuma o lo guarde en el Knowledge Graph?",
            )


def _monitor_loop() -> None:
    global _LAST_WINDOW, _LAST_CLIPBOARD, _LAST_SCREEN_HASH

    window_counter: int = 0
    clipboard_counter: int = 0
    screen_counter: int = 0

    while _running:
        window_counter += 1
        clipboard_counter += 1
        screen_counter += 1

        # Window focus check every 500ms
        if window_counter >= 1:
            window_counter = 0
            title, proc_name = _get_foreground_window()
            window_id = f"{title}|{proc_name}"

            if window_id != _LAST_WINDOW:
                _LAST_WINDOW = window_id
                info = _classify_window(title, proc_name)
                log.info("Ventana: %s - %s", info["context"], title[:60])
                if on_window_change:
                    on_window_change(title, proc_name)
                _detect_window_opportunity(title, proc_name, info["context"], info["app"])

        # Clipboard every 3s (reduced from 2s to reduce spam)
        if clipboard_counter >= 6:
            clipboard_counter = 0
            try:
                text = _get_clipboard_text()
                if text and text != _LAST_CLIPBOARD and len(text) > 10:
                    _LAST_CLIPBOARD = text
                    if on_clipboard_change:
                        on_clipboard_change(text)
                    _detect_clipboard_opportunity(text)
            except Exception as e:
                log.debug("clipboard monitor error: %s", e)

        # Screen change detection every 30s
        if screen_counter >= 60:
            screen_counter = 0
            try:
                h = _get_screen_hash()
                if h and h != _LAST_SCREEN_HASH:
                    changed = _LAST_SCREEN_HASH != ""
                    _LAST_SCREEN_HASH = h
                    if changed and on_screen_change:
                        on_screen_change()
            except Exception as e:
                log.debug("screen monitor error: %s", e)

        time.sleep(0.5)
