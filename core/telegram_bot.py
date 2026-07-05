from __future__ import annotations

"""
Bot de Telegram para TUTUS.
Requiere: BOT_TOKEN en environment o config.

Uso: from core.telegram_bot import start_bot, stop_bot
"""
import logging
import os
import threading
from pathlib import Path
from typing import Any

log = logging.getLogger("tutus.telegram_bot")


TOKEN_KEY: str = "TUTUS_BOT_TOKEN"
_bot_thread: threading.Thread | None = None
_application: Any = None


def _get_token() -> str:
    token = os.getenv(TOKEN_KEY)
    if token:
        return token
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith(TOKEN_KEY + "="):
                return line.split("=", 1)[1].strip().strip("\"'")
    return ""


def start_bot() -> None:
    global _bot_thread, _application

    token = _get_token()
    if not token:
        log.info("[TelegramBot] No TUTUS_BOT_TOKEN en env ni .env. Bot desactivado.")
        log.info("  Crea un bot en @BotFather y agrega TUTUS_BOT_TOKEN=tu_token a .env")
        return

    global _application
    try:
        from telegram.ext import Application, MessageHandler, filters
    except ImportError:
        log.warning("[TelegramBot] python-telegram-bot no instalado. pip install python-telegram-bot")
        return

    def _run_bot() -> None:
        global _application
        try:
            app = Application.builder().token(token).build()
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_message))
            _application = app
            log.info("[TelegramBot] Bot iniciado. Busca tu bot en Telegram.")
            app.run_polling()
        except Exception as e:
            log.error("[TelegramBot] Error: %s", e)

    _bot_thread = threading.Thread(target=_run_bot, daemon=True)
    _bot_thread.start()


def stop_bot() -> None:
    global _application
    if _application:
        try:
            _application.stop()
        except Exception as e:
            log.debug("telegram stop error: %s", e)


async def _handle_message(update: Any, context: Any) -> None:
    try:
        if not update.message or not update.message.text:
            return
        user_text = update.message.text.strip()
        if not user_text:
            return
        user_name = update.message.from_user.first_name or "Usuario"

        log.info("[TelegramBot] %s: %s", user_name, user_text[:80])

        from core.agent_router import route

        result = route(user_text)
        message = result.get("message") or "Listo."
        await update.message.reply_text(message[:4000])

    except Exception as e:
        try:
            await update.message.reply_text(f"Error: {str(e)[:200]}")
        except Exception as e:
            log.debug("telegram handler reply error: %s", e)
