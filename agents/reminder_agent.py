from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from typing import Any

from agents.base_agent import BaseAgent

log = logging.getLogger("tutus.reminder_agent")


class ReminderAgent(BaseAgent):
    name = "ReminderAgent"
    domain = "reminder"
    system_prompt = """Eres el agente de recordatorios de TUTUS.
Tu trabajo es gestionar recordatorios y alarmas para David.

Acciones disponibles:
{
    "action": "add_reminder",
    "params": {"text": "qué recordar", "when": "HH:MM o ISO8601", "recurring": null},
    "message": "texto para David"
}
{
    "action": "list_reminders",
    "params": {},
    "message": "texto"
}
{
    "action": "delete_reminder",
    "params": {"reminder_id": 123},
    "message": "texto"
}

Ejemplos:
- "recuérdame comprar leche a las 5pm" → add_reminder with when="17:00"
- "recuérdame todos los días a las 8am tomar agua" → add_reminder with recurring="daily"
- "qué recordatorios tengo" → list_reminders
- "elimina el recordatorio 3" → delete_reminder with reminder_id=3"""

    def load_skills(self) -> None:
        from core.reminder import add_reminder, delete_reminder, list_reminders

        self.skills = {
            "add_reminder": add_reminder,
            "list_reminders": list_reminders,
            "delete_reminder": delete_reminder,
        }

    def think(self, classification: dict[str, Any], original_message: str, on_token: Callable[[str], None] | None = None) -> dict[str, Any]:
        from core.streamer import stream_chat

        context = self.get_context()
        system = self.system_prompt
        if context:
            system += f"\n\n{context}"

        user_content = f"""Mensaje original: "{original_message}"
Dominio: {classification.get("domain")}
Intención: {classification.get("intent")}
Query: {classification.get("query")}

Decide qué acción ejecutar y con qué parámetros.
Responde SOLO con JSON válido."""

        raw = stream_chat(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            temperature=0.1,
            max_tokens=512,
            on_token=on_token,
        )

        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end != 0:
            try:
                json_str = raw[start:end]
                json_str = re.sub(r':\s*"null"', ": null", json_str)
                json_str = re.sub(r':\s*"none"', ": null", json_str)
                return json.loads(json_str)  # type: ignore[no-any-return]
            except Exception as e:
                log.debug("reminder JSON parse error: %s", e)

        return {"action": "none", "params": {}, "message": raw}
