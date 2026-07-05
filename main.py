from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

os.chdir(Path(__file__).resolve().parent)

from core.log import setup_logger

log = setup_logger("tutus")


def main() -> None:
    from PyQt6.QtWidgets import QApplication

    from core.engine import TutusEngine
    from ui.window import TutusWindow

    engine = TutusEngine()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    window = TutusWindow(engine)
    window.show()

    def on_proactive_suggestion(message: str, pattern: dict[str, Any]) -> None:
        window.add_message("TUTUS", f"💡 {message}", role="assistant")
        try:
            from core.tts import speak

            speak(message)
        except Exception as e:
            log.debug("proactive tts error: %s", e)

    def on_reminder_notification(text: str) -> None:
        window.add_message("TUTUS", text, role="assistant")
        window.show_window()
        try:
            from core.tts import speak

            speak(text)
        except Exception as e:
            log.debug("reminder tts error: %s", e)

    def on_opportunity(context: str, message: str) -> None:
        window.show_suggestion(context, message)

    def _on_startup_progress(msg: str) -> None:
        window._on_startup_progress(msg)

    engine.bootstrap_async(on_progress=_on_startup_progress)

    engine.start_proactive(on_proactive_suggestion)
    engine.start_reminders(on_reminder_notification)
    engine.start_context_monitor(on_opportunity)
    engine.start_telegram_bot()
    engine.start_web_server()
    log.info("Web UI: http://%s:8080", engine.get_web_ip())

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
