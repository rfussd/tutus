from __future__ import annotations

import logging
import time
import urllib.parse

from skills.browser_skill import _ensure_browser

log = logging.getLogger("tutus.youtube_skill")


def youtube_play(query: str) -> str:
    try:
        page = _ensure_browser()
        page.goto(
            f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}",
            timeout=20000,
        )
        time.sleep(2)
        try:
            first = page.locator("ytd-video-renderer #video-title").first
            first.wait_for(timeout=8000)
            first.click()
        except Exception as e:
            log.debug("youtube video click error: %s", e)
            try:
                page.keyboard.press("Tab")
                page.keyboard.press("Tab")
                page.keyboard.press("Enter")
            except Exception as e2:
                log.debug("youtube keyboard fallback error: %s", e2)
        return f"Reproduciendo en YouTube: {query}"
    except Exception as e:
        return f"Error YouTube: {str(e)}"
