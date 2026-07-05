from __future__ import annotations

import json
import logging
import re
from typing import Any

import requests

from core.config import LM_STUDIO_URL, MODEL_ID, TIMEOUT_CLASSIFY
from core.conversation import add_to_buffer, get_buffer  # noqa: F401

log = logging.getLogger("tutus.orchestrator")

ORCHESTRATOR_PROMPT: str = """Clasifica en dominio + JSON. Sin texto extra.
Usa CHAT para conversación normal, RESEARCH solo si la persona PIDE explícitamente investigar/buscar en internet.

REGLAS:
- CHAT: saludos, preguntas personales, opiniones, explicaciones simples, identidad del asistente, follow-ups
- RESEARCH: SOLO cuando usan palabras como "investiga", "busca en internet", "qué hay de nuevo", "noticias", "últimas"
- KNOWLEDGE: preguntar qué sabe TUTUS de la persona ("qué sabes de mí", "recuerdas algo sobre")
- Todo lo demás: domains específicos (music, system, computer, etc.)

Dominios: music, files, docs, system, vision, windows, memory, research, code, reminder, computer, knowledge, dev, browser, chat

"hola" → {"domain":"chat","intent":"greet","confidence":0.99}
"quien eres" → {"domain":"chat","intent":"identity","confidence":0.99}
"como te llamas" → {"domain":"chat","intent":"identity","confidence":0.99}
"que opinas de la inteligencia artificial" → {"domain":"chat","intent":"opinion","query":"inteligencia artificial","confidence":0.95}
"quien crees que va a ganar el mundial" → {"domain":"chat","intent":"opinion","query":"quien gana el mundial","confidence":0.95}
"explica la teoría de cuerdas" → {"domain":"chat","intent":"explain","query":"teoria de cuerdas","confidence":0.95}
"que es machine learning" → {"domain":"chat","intent":"explain","query":"machine learning","confidence":0.95}
"dime sobre la historia de México" → {"domain":"chat","intent":"explain","query":"historia de México","confidence":0.95}
"gracias" → {"domain":"chat","intent":"gratitude","confidence":0.99}
"investiga sobre IA" → {"domain":"research","intent":"web_search","query":"inteligencia artificial","confidence":0.98}
"busca en internet el clima" → {"domain":"research","intent":"web_search","query":"clima hoy","confidence":0.98}
"que hay de nuevo sobre python" → {"domain":"research","intent":"web_search","query":"python novedades","confidence":0.98}
"noticias de tecnologia" → {"domain":"research","intent":"web_search","query":"noticias tecnologia","confidence":0.98}
"que sabes de mi" → {"domain":"knowledge","intent":"query","query":"yo","confidence":0.95}
"recuerdas algo sobre spotify" → {"domain":"knowledge","intent":"query","query":"spotify","confidence":0.95}
"recuerdame algo a las 3pm" → {"domain":"reminder","intent":"add","query":"algo","confidence":0.95}
"mueve el mouse a la derecha" → {"domain":"computer","intent":"control","query":"mueve el mouse","confidence":0.97}
"abre Spotify" → {"domain":"system","intent":"launch","query":"Spotify","confidence":0.95}
"abre youtube" → {"domain":"system","intent":"open_browser","query":"https://youtube.com","confidence":0.95}
"pon jose jose" → {"domain":"music","intent":"play","query":"jose jose","confidence":0.95}
"busca gatos en google" → {"domain":"browser","intent":"navigate","query":"gatos","confidence":0.98}
"ejecuta print(1)" → {"domain":"code","intent":"run_python","query":"print(1)","confidence":0.95}"""


def classify(message: str) -> dict[str, Any]:
    try:
        messages = [{"role": "system", "content": ORCHESTRATOR_PROMPT}]

        # Agregar contexto conversacional
        buf = get_buffer()
        if buf:
            context = "\n".join([f"{m['role']}: {m['content']}" for m in buf[-6:]])
            messages.append(
                {
                    "role": "system",
                    "content": (
                        f"Contexto reciente de la conversación:\n{context}\n\nClasifica el siguiente mensaje considerando este contexto."
                    ),
                }
            )

        messages.append({"role": "user", "content": message})

        response = requests.post(
            LM_STUDIO_URL,
            json={
                "model": MODEL_ID,
                "messages": messages,
                "temperature": 0.0,
                "max_tokens": 150,
                "stream": False,
            },
            timeout=TIMEOUT_CLASSIFY,
        )

        data = response.json()
        raw = data["choices"][0]["message"]["content"].strip()
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

        try:
            from core.schemas import _extract_json

            extracted = _extract_json(raw)
            parsed = json.loads(extracted)
            return parsed  # type: ignore[no-any-return]
        except (ValueError, json.JSONDecodeError):
            pass

    except Exception as e:
        log.error("classify error: %s", e)

    return {"domain": "chat", "intent": "unknown", "query": message, "platform": None, "confidence": 0.0}


def detect_multi_intent(message: str) -> list[str]:
    separators = [
        r"\s+y\s+",
        r"\s+y también\s+",
        r"\s+además\s+",
        r"\s+también\s+",
        r",\s+",
    ]
    for sep in separators:
        parts = re.split(sep, message)
        if len(parts) >= 2:
            clean = [p.strip().strip(",").strip() for p in parts if len(p.strip()) > 5]
            if len(clean) >= 2:
                return clean
    return []


def route_parallel(messages: list[str]) -> list[dict[str, Any]]:
    import threading

    from core.agent_router import route

    results: list[dict[str, Any] | None] = [None] * len(messages)

    def _route(idx: int, msg: str) -> None:
        nonlocal results
        try:
            results[idx] = route(msg)
        except Exception as e:
            results[idx] = {"domain": "error", "message": f"Error: {e}"}

    threads = []
    for i, msg in enumerate(messages):
        t = threading.Thread(target=_route, args=(i, msg), daemon=True)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    return [r for r in results if r is not None]
