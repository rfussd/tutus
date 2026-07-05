from __future__ import annotations

import logging
import re

import requests

from core.config import CONTEXT_SUMMARY_THRESHOLD, LM_STUDIO_URL, MODEL_ID
from core.conversation import add_to_buffer, get_buffer

log = logging.getLogger("tutus.context")

SUMMARY_PROMPT: str = """Resume la siguiente conversación entre un usuario y su asistente TUTUS.
Conserva: datos personales, preferencias, tareas pendientes, información importante.
Omite: saludos, cortesías, repeticiones.
Responde en español, máximo 3 oraciones.
No agregues explicaciones, solo el resumen.

Conversación:
{conversation}"""

_conversation_summary: str = ""


def get_summary() -> str:
    global _conversation_summary
    return _conversation_summary


def summarize_conversation() -> None:
    global _conversation_summary
    buf = get_buffer()
    if not buf:
        return

    history = "\n".join(f"{m['role']}: {m['content']}" for m in buf)
    try:
        response = requests.post(
            LM_STUDIO_URL,
            json={
                "model": MODEL_ID,
                "messages": [{"role": "system", "content": SUMMARY_PROMPT.format(conversation=history)}],
                "temperature": 0.3,
                "max_tokens": 256,
                "stream": False,
            },
            timeout=30,
        )
        data = response.json()
        summary = data["choices"][0]["message"]["content"].strip()
        summary = re.sub(r"<think>.*?</think>", "", summary, flags=re.DOTALL).strip()
        _conversation_summary = summary

    except Exception as e:
        log.error("summarization error: %s", e)


def auto_summarize_if_needed() -> None:
    buf = get_buffer()
    if len(buf) >= CONTEXT_SUMMARY_THRESHOLD * 2:
        summarize_conversation()
        keep = buf[-4:]
        buf[:] = keep
        add_to_buffer("system", f"[Resumen de la conversación anterior: {_conversation_summary}]")
