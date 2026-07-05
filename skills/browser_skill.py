from __future__ import annotations

import base64
import logging
import os
from typing import Any

from playwright.sync_api import sync_playwright

log = logging.getLogger("tutus.browser_skill")


_page: Any = None
_playwright: Any = None
_browser: Any = None


def _ensure_browser() -> Any:
    global _page, _playwright, _browser
    try:
        if _page is not None and not _page.is_closed():
            return _page
    except Exception as e:
        log.debug("browser page check error: %s", e)
        _page = None

    if _browser is not None:
        try:
            _browser.close()
        except Exception as e:
            log.debug("browser close error: %s", e)
        _browser = None

    if _playwright is not None:
        try:
            _playwright.stop()
        except Exception as e:
            log.debug("playwright stop error: %s", e)

    _playwright = sync_playwright().start()

    brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

    if os.path.exists(brave_path):
        _browser = _playwright.chromium.launch(
            headless=False,
            executable_path=brave_path,
            args=["--start-maximized"],
        )
    elif os.path.exists(chrome_path):
        _browser = _playwright.chromium.launch(
            headless=False,
            channel="chrome",
            args=["--start-maximized"],
        )
    else:
        _browser = _playwright.chromium.launch(
            headless=False,
            args=["--start-maximized"],
        )

    ctx = _browser.new_context(no_viewport=True)
    _page = ctx.new_page()
    return _page


def close_browser() -> None:
    global _page, _browser, _playwright
    try:
        if _page and not _page.is_closed():
            _page.close()
        if _browser:
            _browser.close()
        if _playwright:
            _playwright.stop()
    except Exception as e:
        log.debug("close_browser error: %s", e)
    _page = None
    _browser = None
    _playwright = None


def navigate(url: str) -> str:
    if not url.startswith("http"):
        url = f"https://{url}"
    page = _ensure_browser()
    try:
        page.goto(url, timeout=30000)
        return f"Navegando a: {url}"
    except Exception as e:
        return f"Error navegando: {e}"


def get_page_text() -> str:
    page = _ensure_browser()
    try:
        text = page.inner_text("body")
        return text[:2000] if text else "(pagina vacia)"
    except Exception as e:
        return f"Error leyendo pagina: {e}"


def get_page_title() -> str:
    page = _ensure_browser()
    try:
        return page.title()  # type: ignore[no-any-return]
    except Exception as e:
        return f"Error: {e}"


def click(selector: str) -> str:
    page = _ensure_browser()
    try:
        page.click(selector, timeout=5000)
        return f"Click en: {selector}"
    except Exception as e:
        return f"Error en click: {e}"


def fill(selector: str, text: str) -> str:
    page = _ensure_browser()
    try:
        page.fill(selector, text)
        return f"Texto '{text[:30]}' en {selector}"
    except Exception as e:
        return f"Error en fill: {e}"


def press(key: str) -> str:
    page = _ensure_browser()
    try:
        page.keyboard.press(key)
        return f"Tecla: {key}"
    except Exception as e:
        return f"Error: {e}"


def screenshot() -> str:
    page = _ensure_browser()
    try:
        b64 = base64.b64encode(page.screenshot(type="jpeg", quality=70)).decode("utf-8")
        return b64
    except Exception as e:
        return f"Error: {e}"


def wait(seconds: float = 2.0) -> str:
    import time

    time.sleep(seconds)
    return f"Espera {seconds}s"


def search(query: str) -> str:
    page = _ensure_browser()
    try:
        from urllib.parse import quote

        page.goto(f"https://www.google.com/search?q={quote(query)}", timeout=15000)
        text = page.inner_text("body")
        return text[:1500] if text else "(sin resultados)"
    except Exception as e:
        return f"Error: {e}"


def extract_links() -> str:
    page = _ensure_browser()
    try:
        links = page.eval_on_selector_all(
            "a[href]", "elements => elements.map(e => ({text: e.innerText.trim(), href: e.href})).filter(e => e.text).slice(0, 20)"
        )
        return "\n".join(f"{ln['text'][:60]} → {ln['href']}" for ln in links)
    except Exception as e:
        return f"Error: {e}"
