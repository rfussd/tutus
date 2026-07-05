from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

log = logging.getLogger("tutus.reminder")

_reminder_conn: Any = None


def get_connection() -> Any:
    from core.memory_signals import get_connection as _get_mem_conn

    return _get_mem_conn()


def init_reminders_db() -> None:
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            remind_at TEXT NOT NULL,
            recurring TEXT,
            category TEXT DEFAULT 'general',
            created_at TEXT NOT NULL,
            done INTEGER DEFAULT 0
        )
    """)
    conn.commit()


init_reminders_db()

_notify_callback: Callable[[str], None] | None = None


def set_notify_callback(fn: Callable[[str], None]) -> None:
    global _notify_callback
    _notify_callback = fn


def add_reminder(text: str, when: str, recurring: str | None = None) -> str:
    try:
        remind_at = datetime.fromisoformat(when).isoformat()
    except ValueError:
        try:
            now = datetime.now()
            parts = when.split(":")
            if len(parts) == 2:
                hour, minute = int(parts[0]), int(parts[1])
                remind_at_dt = now.replace(hour=hour, minute=minute, second=0)
                if remind_at_dt < now:
                    remind_at_dt += timedelta(days=1)
                remind_at = remind_at_dt.isoformat()
            else:
                return "Formato de hora no válido. Usa HH:MM o ISO8601."
        except Exception as e:
            log.debug("reminder time parse error: %s", e)
            return "Formato de hora no válido."

    conn = get_connection()
    conn.execute(
        "INSERT INTO reminders (text, remind_at, recurring, category, created_at) VALUES (?, ?, ?, ?, ?)",
        (text, remind_at, recurring, "general", datetime.now().isoformat()),
    )
    conn.commit()
    return f"Recordatorio guardado: '{text}' a las {when}"


def list_reminders() -> str:
    conn = get_connection()
    rows = conn.execute("SELECT id, text, remind_at, recurring, done FROM reminders ORDER BY remind_at ASC LIMIT 20").fetchall()

    if not rows:
        return "No tienes recordatorios."

    output = ["Tus recordatorios:"]
    for r in rows:
        status = "✓" if r["done"] else "○"
        rec = f" (repite: {r['recurring']})" if r["recurring"] else ""
        output.append(f"  {status} [{r['id']}] {r['text']} — {r['remind_at']}{rec}")
    return "\n".join(output)


def delete_reminder(reminder_id: int) -> str:
    conn = get_connection()
    conn.execute("DELETE FROM reminders WHERE id=?", (reminder_id,))
    conn.commit()
    return f"Recordatorio {reminder_id} eliminado."


def _check_reminders() -> None:
    global _notify_callback
    conn = get_connection()
    now = datetime.now().isoformat()
    rows = conn.execute(
        "SELECT * FROM reminders WHERE remind_at <= ? AND done=0",
        (now,),
    ).fetchall()

    for r in rows:
        if _notify_callback:
            _notify_callback(f"⏰ Recordatorio: {r['text']}")

        if r["recurring"]:
            try:
                from dateutil.parser import parse

                old = parse(r["remind_at"])
                if r["recurring"] == "daily":
                    new_time = (old + timedelta(days=1)).isoformat()
                elif r["recurring"] == "weekly":
                    new_time = (old + timedelta(weeks=1)).isoformat()
                elif r["recurring"] == "hourly":
                    new_time = (old + timedelta(hours=1)).isoformat()
                else:
                    new_time = (old + timedelta(days=1)).isoformat()
                conn.execute(
                    "UPDATE reminders SET remind_at=? WHERE id=?",
                    (new_time, r["id"]),
                )
            except Exception as e:
                log.debug("reminder recurring update error: %s", e)
                conn.execute("UPDATE reminders SET done=1 WHERE id=?", (r["id"],))
        else:
            conn.execute("UPDATE reminders SET done=1 WHERE id=?", (r["id"],))

    conn.commit()


_reminder_thread_running = False


def start_reminder_engine(callback: Callable[[str], None]) -> None:
    global _reminder_thread_running, _notify_callback
    _notify_callback = callback
    if _reminder_thread_running:
        return

    _reminder_thread_running = True

    def _run() -> None:
        while _reminder_thread_running:
            _check_reminders()
            time.sleep(30)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    log.info("Motor de recordatorios activo")
