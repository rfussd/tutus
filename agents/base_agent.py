from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from typing import Any

import requests

from core.config import LM_STUDIO_URL, MODEL_ID, STREAMING_ENABLED

log = logging.getLogger("tutus.base_agent")


class BaseAgent:
    name: str = "BaseAgent"
    domain: str = "base"
    system_prompt: str = ""

    def __init__(self) -> None:
        self.skills: dict[str, Callable[..., str]] = {}
        self.load_skills()

    def load_skills(self) -> None:
        pass

    def get_context(self) -> str:
        from core.memory_signals import get_context_for_domain

        return get_context_for_domain(self.domain)

    def get_user_profile(self) -> str:
        try:
            from core.user_profile import get_user_profile_summary

            return get_user_profile_summary()
        except Exception as e:
            log.debug("get_user_profile error: %s", e)
            return ""

    def _parse_llm_json(self, raw: str) -> dict[str, Any]:
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end != 0:
            json_str = raw[start:end]
            json_str = re.sub(r':\s*"null"', ": null", json_str)
            json_str = re.sub(r":\s*none(?=[,\s}])", ": null", json_str)
            json_str = re.sub(r'(?<=: ")(.*?)(?=")', lambda m: m.group(0).replace("\n", "\\n"), json_str, flags=re.DOTALL)
            return json.loads(json_str)  # type: ignore[no-any-return]
        return {"action": "none", "params": {}, "message": raw}

    def _llm_call(
        self,
        system: str,
        user: str,
        temperature: float = 0.1,
        max_tokens: int = 512,
        timeout: int = 30,
        on_token: Callable[[str], None] | None = None,
        images: list[str] | None = None,
    ) -> str:
        if STREAMING_ENABLED and on_token:
            from core.streamer import stream_chat

            return stream_chat(
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=temperature,
                max_tokens=max_tokens,
                on_token=on_token,
            )
        messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
        if images:
            content: list[dict[str, Any]] = [{"type": "text", "text": user}]
            for img in images:
                content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}})
            messages.append({"role": "user", "content": content})
        else:
            messages.append({"role": "user", "content": user})
        response = requests.post(
            LM_STUDIO_URL,
            json={"model": MODEL_ID, "messages": messages, "temperature": temperature, "max_tokens": max_tokens, "stream": False},
            timeout=timeout,
        )
        return response.json()["choices"][0]["message"]["content"].strip()  # type: ignore[no-any-return]

    def think(self, classification: dict[str, Any], original_message: str, on_token: Callable[[str], None] | None = None) -> dict[str, Any]:
        context = self.get_context()
        profile = self.get_user_profile()

        system = self.system_prompt
        if context:
            system += f"\n\nContexto relevante:\n{context}"
        if profile:
            system += f"\n\nPerfil de David:\n{profile}"

        user_content = f"""
Mensaje original: "{original_message}"
Dominio: {classification.get("domain")}
Intención: {classification.get("intent")}
Query: {classification.get("query")}
Platform: {classification.get("platform")}

Decide qué acción ejecutar y con qué parámetros.
Responde SOLO con JSON válido.
"""

        try:
            raw = self._llm_call(system, user_content, on_token=on_token)
            log.debug("[%s] RAW: %s...", self.name, raw[:120])
            return self._parse_llm_json(raw)
        except (KeyError, IndexError) as e:
            log.warning("[%s] Parse error - key/index missing: %s", self.name, e)
        except (json.JSONDecodeError, UnboundLocalError) as e:
            log.warning("[%s] Parse error: %s", self.name, e)
        except Exception as e:
            log.error("[%s] Error en think: %s", self.name, e)

        return {"action": "none", "params": {}, "message": "No pude procesar eso."}

    def execute(self, decision: dict[str, Any]) -> str:
        action = decision.get("action", "none")
        params = decision.get("params", {})

        if action == "none":
            return decision.get("message", "")  # type: ignore[no-any-return]

        skill = self.skills.get(action)
        if skill:
            try:
                return skill(**params)
            except Exception as e:
                return f"Error ejecutando {action}: {str(e)}"

        return f"Acción '{action}' no disponible en {self.name}"

    def handle(self, classification: dict[str, Any], original_message: str, on_token: Callable[[str], None] | None = None) -> str:
        decision = self.think(classification, original_message, on_token=on_token)
        message = decision.get("message", "Listo.")
        result = self.execute(decision)
        self._learn(classification, decision, original_message)

        if result and result != message:
            return result
        return result or message

    def _learn(self, classification: dict[str, Any], decision: dict[str, Any], original_message: str = "") -> None:
        try:
            if original_message:
                from core.knowledge_graph import get_knowledge_graph

                kg = get_knowledge_graph()
                kg.add_triples_from_text(original_message, use_llm=True)
        except Exception as e:
            log.debug("[%s] Auto-learn error: %s", self.name, e)


class StepwiseTaskAgent(BaseAgent):
    """Agent that executes a multi-step task by repeatedly calling the LLM
    until it returns action='done' or max_steps is reached."""

    max_steps: int = 15
    task_timeout: int = 90

    def think(self, classification: dict[str, Any], original_message: str, on_token: Callable[[str], None] | None = None) -> dict[str, Any]:
        return {"action": "none", "params": {}, "message": ""}

    def execute(self, decision: dict[str, Any]) -> str:
        return decision.get("message", "")  # type: ignore[no-any-return]

    def _build_user_message(self, task: str, step: int, history: str) -> str:
        return f"""Paso {step}/{self.max_steps}
Tarea: {task}
Historial:
{history}
¿Cuál es la siguiente acción? Una sola. Responde SOLO con JSON."""

    def _get_extra_images(self) -> list[str]:
        return []

    def handle(self, classification: dict[str, Any], original_message: str, on_token: Callable[[str], None] | None = None) -> str:
        task = classification.get("query") or original_message
        log_entries = [f"Tarea: {task}"]
        step = 0

        while step < self.max_steps:
            step += 1
            log.info("[%s] Paso %s/%s", self.name, step, self.max_steps)
            history = "\n".join(log_entries[-10:])
            user_msg = self._build_user_message(task, step, history)

            try:
                images = self._get_extra_images()
                raw = self._llm_call(
                    self.system_prompt, user_msg, temperature=0.1, max_tokens=1024, timeout=self.task_timeout, images=images
                )
                decision = self._parse_llm_json(raw)
                action = decision.get("action", "")
                params = decision.get("params", {})
                msg = decision.get("message", "")
            except Exception as e:
                log_entries.append(f"  -> Error LLM: {e}")
                continue

            if action == "done":
                return f"{msg or 'Tarea completada.'}\n\nPasos:\n" + "\n".join(log_entries)

            tool_fn = self.skills.get(action)
            if tool_fn:
                try:
                    result = tool_fn(**params)
                    log_entries.append(f"  Paso {step}: {action} -> {str(result)[:200]}")
                except Exception as e:
                    log_entries.append(f"  Paso {step}: {action} error: {e}")
                import time

                time.sleep(0.3)
            else:
                log_entries.append(f"  Paso {step}: Acción desconocida: {action}")
                break

        return f"No pude completar la tarea en {self.max_steps} pasos.\n" + "\n".join(log_entries[-8:])
