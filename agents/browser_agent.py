from __future__ import annotations

from typing import Any

from agents.base_agent import StepwiseTaskAgent

BROWSER_PROMPT = """Controlas Chrome para David. Acciones: navigate, search, get_page_text, get_page_title, click, fill, press, extract_links, screenshot, wait, close_browser, done

{"action":"navigate","params":{"url":"google.com"}}
{"action":"search","params":{"query":"clima"}}
{"action":"done","params":{"message":"listo"}}"""


class BrowserAgent(StepwiseTaskAgent):
    name = "BrowserAgent"
    domain = "browser"
    system_prompt = BROWSER_PROMPT
    max_steps = 15
    task_timeout = 60

    def load_skills(self) -> None:
        from skills.browser_skill import (
            click,
            close_browser,
            extract_links,
            fill,
            get_page_text,
            get_page_title,
            navigate,
            press,
            screenshot,
            search,
            wait,
        )

        self.skills: dict[str, Any] = {
            "navigate": navigate,
            "get_page_text": get_page_text,
            "get_page_title": get_page_title,
            "click": click,
            "fill": fill,
            "press": press,
            "search": search,
            "extract_links": extract_links,
            "wait": wait,
            "screenshot": screenshot,
            "close_browser": close_browser,
        }
