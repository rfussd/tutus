"""
Bot de WhatsApp Web usando Playwright.
Requiere: escanear QR una vez (se guarda la sesion en data/wadata/).

Uso: from skills.whatsapp_bot import start_whatsapp, stop_whatsapp, send_message
"""

from __future__ import annotations

import logging
import os
import queue
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

DATA_DIR: Path = Path(__file__).parent.parent / "data" / "wadata"
_playwright: Any = None
_browser: Any = None
_page: Any = None
_listener_thread: threading.Thread | None = None
_running: bool = False
_message_queue: queue.Queue[Any] = queue.Queue()
_on_message: Callable[..., Any] | None = None
log = logging.getLogger("tutus.whatsapp")


def _get_page() -> Any:
    global _playwright, _browser, _page
    if _page and not _page.is_closed():
        return _page

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _playwright = sync_playwright().start()
    try:
        _browser = _playwright.chromium.launch_persistent_context(
            str(DATA_DIR),
            headless=False,
            args=["--start-maximized"],
        )
    except Exception as e:
        log.debug("default browser launch failed: %s", e)
        # Try common browser paths as fallback
        _browser = None
        browser_paths = [
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\Mozilla Firefox\firefox.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]
        for bp in browser_paths:
            if os.path.exists(bp):
                try:
                    _browser = _playwright.chromium.launch_persistent_context(
                        str(DATA_DIR),
                        headless=False,
                        executable_path=bp,
                        args=["--start-maximized"],
                    )
                    log.info("Usando navegador: %s", bp)
                    break
                except Exception as e:
                    log.debug("browser %s failed: %s", bp, e)
                    continue

    if _browser is None:
        raise RuntimeError("No se pudo iniciar el navegador para WhatsApp")

    _page = _browser.pages[0] if _browser.pages else _browser.new_page()
    return _page


def start_whatsapp(on_message_callback: Callable[..., Any] | None = None) -> None:
    global _listener_thread, _running, _on_message
    _on_message = on_message_callback
    _running = True

    page = _get_page()
    page.goto("https://web.whatsapp.com", timeout=60000)
    log.info("Abriendo WhatsApp Web. Escanea el QR si es necesario.")
    log.info("Esperando carga...")

    try:
        page.wait_for_selector('[data-testid="conversation-panel-messages"]', timeout=120000)
        log.info("Sesion activa!")
    except Exception:
        log.warning("Esperando QR... espera hasta 3 minutos.")
        try:
            page.wait_for_selector('[data-testid="conversation-panel-messages"]', timeout=180000)
            log.info("Sesion activa!")
        except Exception:
            log.error("No se pudo iniciar sesion. Revisa el QR.")
            return

    _listener_thread = threading.Thread(target=_listen_loop, daemon=True)
    _listener_thread.start()
    log.info("Bot de WhatsApp activo")


def stop_whatsapp() -> None:
    global _running, _page, _browser, _playwright
    _running = False
    try:
        if _page and not _page.is_closed():
            _page.close()
    except Exception as e:
        log.warning("page close error: %s", e)
    try:
        if _browser:
            _browser.close()
    except Exception as e:
        log.warning("browser close error: %s", e)
    try:
        if _playwright:
            _playwright.stop()
    except Exception as e:
        log.warning("playwright stop error: %s", e)
    _page = None
    _browser = None
    _playwright = None


def send_message(contact_or_group: str, text: str) -> str:
    page = _get_page()
    try:
        search_box = page.locator('[data-testid="chat-list-search"]')
        search_box.fill(contact_or_group)
        time.sleep(1)

        contact = page.locator(f'[data-testid="conversation-title"]:has-text("{contact_or_group}")')
        if contact.count() == 0:
            contact = page.locator(f'[title="{contact_or_group}"]')
        contact.first.click()
        time.sleep(0.5)

        msg_box = page.locator('[data-testid="conversation-compose-box-input"]')
        msg_box.fill(text)
        page.locator('[data-testid="compose-btn-send"]').click()
        return f"Mensaje enviado a {contact_or_group}"
    except Exception as e:
        return f"Error enviando mensaje: {e}"


def _listen_loop() -> None:
    global _page
    last_messages = set()

    while _running:
        try:
            page = _get_page()
            messages = page.locator('[data-testid="conversation-panel-messages"] .message-in')

            current_contact = "desconocido"
            try:
                title_elem = page.locator('[data-testid="conversation-title"]')
                if title_elem.count() > 0:
                    current_contact = title_elem.inner_text()
            except Exception as e:
                log.warning("title read error: %s", e)

            for i in range(messages.count()):
                try:
                    msg_elem = messages.nth(i)
                    msg_id = msg_elem.get_attribute("data-id") or str(i)
                    if msg_id in last_messages:
                        continue

                    text = msg_elem.inner_text()
                    contact = current_contact

                    if text and _on_message and len(text) > 2:
                        last_messages.add(msg_id)
                        if len(last_messages) > 200:
                            last_messages.clear()
                        _on_message(text, contact)
                except Exception as e:
                    log.warning("message processing error: %s", e)
        except Exception as e:
            log.warning("listen loop error: %s", e)

        time.sleep(2)
