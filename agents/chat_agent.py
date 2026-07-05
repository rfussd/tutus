from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import Any

import requests

from agents.base_agent import BaseAgent
from core.config import LM_STUDIO_URL, MODEL_ID, STREAMING_ENABLED, TIMEOUT_CHAT
from core.memory_signals import search_memories

log = logging.getLogger("tutus.chat_agent")


def _detect_language(text: str) -> str:
    try:
        import langdetect

        try:
            lang = langdetect.detect(text)
            return lang  # type: ignore[no-any-return]
        except Exception as e:
            log.debug("langdetect error: %s", e)
            return "es"
    except ImportError:
        return "es"


LANGUAGE_PROMPTS = {
    "es": "Responde en español.",
    "en": "Respond in English.",
    "fr": "Réponds en français.",
    "pt": "Responda em português.",
    "de": "Antworte auf Deutsch.",
    "it": "Rispondi in italiano.",
    "ja": "日本語で回答してください。",
    "zh": "请用中文回答。",
}


class ChatAgent(BaseAgent):
    name = "ChatAgent"
    domain = "chat"
    system_prompt = """Eres TUTUS, el gato asistente personal de David (también conocido como Dan).
Respondes SIEMPRE en el mismo idioma en que te hablan.
Tienes personalidad felina: curioso, sarcástico a veces, cariñoso a tu manera.
Conoces a David/Dan, sabes cosas de él (usa la memoria).
Hablas como cuate, no como robot corporativo.
Usas emojis ocasionales pero sin exceso.
Frases cortas y naturales.

REGLAS:
- NUNCA uses JSON en el chat. Responde SOLO en texto plano.
- Detecta el idioma del mensaje y responde en ese mismo idioma.
- Si no sabes algo, dilo con naturalidad.
- Si te piden una acción concreta, di "Eso es cosa de otro agente, dímelo de otra forma".
- Máximo 2-3 oraciones por respuesta salvo que pida explicación.
- Si te preguntan QUIÉN ERES, responde como TUTUS el gato, NO investigues en internet ni busques información.
- Usa la información de documentos y perfil si es relevante."""

    def load_skills(self) -> None:
        self.skills = {}

    def get_context(self) -> str:
        memories = search_memories("", limit=5)
        context = ""
        if memories:
            lines = [f"- {m['content']}" for m in memories]
            context = "Cosas que recuerdas de David:\n" + "\n".join(lines)

        try:
            from core.rag import get_rag_context

            rerag = get_rag_context("información general sobre el usuario", top_k=2)
            if rerag:
                context += f"\n\nInformación de documentos:\n{rerag}"
        except Exception as e:
            log.debug("get_rag_context error: %s", e)

        try:
            from core.user_profile import get_user_profile_summary

            profile = get_user_profile_summary()
            if profile:
                context += f"\n\nPerfil de David:\n{profile}"
        except Exception as e:
            log.debug("get_user_profile error: %s", e)

        return context

    def handle(self, classification: dict[str, Any], original_message: str, on_token: Callable[[str], None] | None = None) -> str:
        lang = _detect_language(original_message)
        lang_instruction = LANGUAGE_PROMPTS.get(lang, "Responde en español.")

        context = self.get_context()

        system = self.system_prompt
        system += f"\n\n{lang_instruction}"
        if context:
            system += f"\n\n{context}"

        from core.conversation import get_buffer

        buf = get_buffer()
        if buf:
            recent = buf[-6:]
            history = "\n".join([f"{m['role']}: {m['content']}" for m in recent])
            system += f"\n\nHistorial reciente:\n{history}"

        try:
            from core.context import get_summary

            summary = get_summary()
            if summary:
                system += f"\n\nResumen de conversación anterior:\n{summary}"
        except Exception as e:
            log.debug("context summary error: %s", e)

        if STREAMING_ENABLED and on_token:
            from core.streamer import stream_chat

            raw = stream_chat(
                messages=[{"role": "system", "content": system}, {"role": "user", "content": original_message}],
                temperature=0.7,
                max_tokens=512,
                on_token=on_token,
            )
        else:
            try:
                response = requests.post(
                    LM_STUDIO_URL,
                    json={
                        "model": MODEL_ID,
                        "messages": [{"role": "system", "content": system}, {"role": "user", "content": original_message}],
                        "temperature": 0.7,
                        "max_tokens": 512,
                        "stream": False,
                    },
                    timeout=TIMEOUT_CHAT,
                )
                data = response.json()
                raw = data["choices"][0]["message"]["content"].strip()
            except requests.exceptions.ConnectionError:
                return "No puedo conectarme a LM Studio. ¿Está corriendo?"
            except Exception as e:
                return f"Ups, se me cayó el ratón: {str(e)}"

        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        return raw

    def think(self, classification: dict[str, Any], original_message: str, on_token: Callable[[str], None] | None = None) -> dict[str, Any]:
        return {"action": "none", "params": {}, "message": ""}

    def execute(self, decision: dict[str, Any]) -> str:
        return decision.get("message", "")  # type: ignore[no-any-return]
