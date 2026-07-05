from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from datetime import datetime
from typing import Any

import schedule

log = logging.getLogger("tutus.proactive")

_callback: Callable[[str, dict[str, Any]], None] | None = None


def get_connection() -> Any:
    from core.memory_signals import get_connection as _get_mem_conn

    return _get_mem_conn()


def set_callback(fn: Callable[[str, dict[str, Any]], None]) -> None:
    global _callback
    _callback = fn


def log_action(action: str, domain: str, params: dict[str, Any] | None = None) -> None:
    """Registra cada acción ejecutada con timestamp."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS action_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            domain TEXT NOT NULL,
            params TEXT,
            hour INTEGER,
            weekday INTEGER,
            created_at TEXT NOT NULL
        )
    """)
    import json

    now = datetime.now()
    conn.execute(
        "INSERT INTO action_log (action, domain, params, hour, weekday, created_at) VALUES (?,?,?,?,?,?)",
        (action, domain, json.dumps(params or {}), now.hour, now.weekday(), now.isoformat()),
    )
    conn.commit()


def get_patterns() -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT action, domain, hour, weekday, COUNT(*) as freq
            FROM action_log
            GROUP BY action, domain, hour, weekday
            HAVING freq >= 3
            ORDER BY freq DESC
            LIMIT 10
        """).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        log.debug("get_patterns error: %s", e)
        return []


def check_proactive_suggestions() -> None:
    """Revisa si hay algo que TUTUS debería sugerir ahora."""
    now = datetime.now()
    current_hour = now.hour
    current_weekday = now.weekday()

    patterns = get_patterns()
    suggestions = []

    for pattern in patterns:
        # Si el patrón coincide con la hora actual ±1
        if abs(pattern["hour"] - current_hour) <= 1 and pattern["weekday"] == current_weekday:
            suggestions.append(pattern)

    if suggestions and _callback:
        best = suggestions[0]
        dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        msg = f"Oye Dan, normalmente los {dias[current_weekday]} a esta hora {_get_action_description(best)}. ¿Lo hago?"
        _callback(msg, best)


def _get_action_description(pattern: dict[str, Any]) -> str:
    action = pattern["action"]
    domain = pattern["domain"]

    descriptions = {
        "spotify_play": "pones música en Spotify",
        "open_app": "abres una aplicación",
        "youtube_play": "ves YouTube",
        "organize_downloads": "organizas tus descargas",
        "get_weather": "revisas el clima",
        "search_web": "buscas algo en Google",
    }
    return descriptions.get(action, f"haces algo en {domain}")


def start_proactive_engine(callback: Callable[[str, dict[str, Any]], None]) -> None:
    """Inicia el motor proactivo en background."""
    set_callback(callback)

    from core.config import PROACTIVE_CHECK_INTERVAL_MIN

    schedule.every(PROACTIVE_CHECK_INTERVAL_MIN).minutes.do(check_proactive_suggestions)

    def _run() -> None:
        while True:
            schedule.run_pending()
            time.sleep(60)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    log.info("Motor proactivo activo")
