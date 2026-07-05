from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import Any

from core.orchestrator import classify

log = logging.getLogger("tutus.router")

_agents: dict[str, Any] = {}
_pending_action: dict[str, Any] | None = None
_CONFIRM_WORDS: set[str] = {"sí", "si", "ok", "okey", "simon", "sip", "yes", "y", "dale", "adelante", "vamos", "hazlo", "confirmo"}
_CANCEL_WORDS: set[str] = {"no", "nop", "cancel", "para", "detente", "cancela"}

# ── Pre-clasificación: patrones que SIEMPRE van a chat ───────────────
_PRE_CHAT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"^(hola|buenos?\s*(d[ií]as|dias|tardes|noches)|qu[eé]\s*tal|c[oó]mo\s*(est[aá]s|vas)|que\s*haces|saludos)\b", re.IGNORECASE
        ),
        "greet",
    ),
    (
        re.compile(
            r"^(qui[eé]n\s*eres|quien\s*eres|c[oó]mo\s*te\s*llamas|como\s*te\s*llamas|t[uú]\s*qui[eé]n\s*eres|tu\s*quien\s*eres|qu[eé]\s*eres|que\s*eres|qui[eé]n\s*soy|quien\s*soy|sabes\s*qui[eé]n\s*soy)\b",
            re.IGNORECASE,
        ),
        "identity",
    ),
    (
        re.compile(
            r"^(qu[eé]\s*opinas|que\s*opinas|qu[eé]\s*piensas|que\s*piensas|qui[eé]n\s*crees|quien\s*crees|te\s*gusta|crees\s*que|opinas\s*que|qu[eé]\s*te\s*parece|que\s*te\s*parece)\b",
            re.IGNORECASE,
        ),
        "opinion",
    ),
    (re.compile(r"^(gracias|thanks|muchas\s*gracias|te\s*agradezco|agradecido)\b", re.IGNORECASE), "gratitude"),
    (re.compile(r"^(adi[oó]s|adios|hasta\s*luego|nos\s*vemos|bye|chao|ciao|ah[oó]ra\s*me\s*voy)\b", re.IGNORECASE), "farewell"),
    (
        re.compile(
            r"^(por\s*qu[eé]|porque|cu[eé]ntame\s*m[aá]s|dime\s*m[aá]s|expl[ií]came|a\s*hora\s*qu[eé]|ahora\s*que)\b", re.IGNORECASE
        ),
        "follow_up",
    ),
]


def get_agent(domain: str) -> Any | None:
    if domain not in _agents:
        if domain == "music":
            from agents.music_agent import MusicAgent

            _agents[domain] = MusicAgent()
        elif domain == "files":
            from agents.files_agent import FilesAgent

            _agents[domain] = FilesAgent()
        elif domain == "docs":
            from agents.docs_agent import DocsAgent

            _agents[domain] = DocsAgent()
        elif domain == "system":
            from agents.system_agent import SystemAgent

            _agents[domain] = SystemAgent()
        elif domain == "vision":
            from agents.vision_agent import VisionAgent

            _agents[domain] = VisionAgent()
        elif domain == "windows":
            from agents.windows_agent import WindowsAgent

            _agents[domain] = WindowsAgent()
        elif domain == "memory":
            from agents.memory_agent import MemoryAgent

            _agents[domain] = MemoryAgent()
        elif domain == "research":
            from agents.research_agent import ResearchAgent

            _agents[domain] = ResearchAgent()
        elif domain == "code":
            from agents.code_agent import CodeAgent

            _agents[domain] = CodeAgent()
        elif domain == "reminder":
            from agents.reminder_agent import ReminderAgent

            _agents[domain] = ReminderAgent()
        elif domain == "computer":
            from agents.computer_agent import ComputerAgent

            _agents[domain] = ComputerAgent()
        elif domain == "knowledge":
            from agents.knowledge_agent import KnowledgeAgent

            _agents[domain] = KnowledgeAgent()
        elif domain == "dev":
            from agents.project_agent import ProjectAgent

            _agents[domain] = ProjectAgent()
        elif domain == "browser":
            from agents.browser_agent import BrowserAgent

            _agents[domain] = BrowserAgent()
        elif domain == "chat":
            from agents.chat_agent import ChatAgent

            _agents[domain] = ChatAgent()
        else:
            return None
    return _agents[domain]


def route(message: str, on_token: Callable[[str], None] | None = None) -> dict[str, Any]:
    global _pending_action

    from core.context import auto_summarize_if_needed

    auto_summarize_if_needed()

    # ── Manejar confirmación pendiente ─────────────────────────────────
    if _pending_action:
        msg_lower = message.strip().lower().rstrip(".!?")
        if msg_lower in _CANCEL_WORDS:
            _pending_action = None
            return {"message": "✅ Acción cancelada.", "domain": "chat", "action": "cancelled"}
        if msg_lower in _CONFIRM_WORDS:
            action = _pending_action
            _pending_action = None
            return _execute(action["domain"], action["classification"], action["message"])
        # Si no confirma ni cancela, se trata como mensaje normal y se descarta la acción pendiente
        _pending_action = None

    # ── Pre-clasificación: patrones de chat directo (sin LLM) ─────────
    msg_clean = message.strip()
    for pattern, intent in _PRE_CHAT_PATTERNS:
        if pattern.match(msg_clean):
            log.info("Pre-clasificación -> chat/%s", intent)
            classification = {"domain": "chat", "intent": intent, "query": message, "platform": None, "confidence": 0.99}
            return _execute("chat", classification, message, on_token)

    classification = classify(message)
    domain = classification.get("domain", "chat")

    # ── Pedir confirmación para domains físicos ────────────────────────
    if domain in ("computer",):
        _pending_action = {
            "domain": domain,
            "classification": classification,
            "message": message,
        }
        return {
            "message": f'⚠ Voy a controlar tu PC: "{message}". ¿Confirmo? (sí/no)',
            "domain": "chat",
            "action": "confirm",
        }

    return _execute(str(domain), classification, message, on_token)


def _execute(
    domain: str, classification: dict[str, Any], original_message: str, on_token: Callable[[str], None] | None = None
) -> dict[str, Any]:
    log.info("domain=%s intent=%s confidence=%s", domain, classification.get("intent"), classification.get("confidence", 0.0))

    agent = get_agent(domain)
    if not agent:
        return {"message": "No sé cómo manejar eso aún.", "domain": domain, "action": "none", "classification": classification}

    try:
        if domain in ("chat",):
            response = agent.handle(classification, original_message, on_token=on_token)
            return {"message": response, "domain": "chat", "action": "none", "classification": classification}

        response = agent.handle(classification, original_message)

        # Si knowledge no tiene info y la consulta es factual, fallback a research
        if domain == "knowledge":
            resp_lower = response.lower()
            if "no tengo información" in resp_lower or "no sé" in resp_lower or "no encontre" in resp_lower:
                msg_check = original_message.strip().lower()
                factual_triggers = [
                    "qué es",
                    "que es",
                    "qué son",
                    "que son",
                    "quién es",
                    "quien es",
                    "dime sobre",
                    "hablame de",
                    "información sobre",
                    "explica",
                    "investiga",
                    "qué significa",
                    "que significa",
                ]
                is_factual = any(msg_check.startswith(t) for t in factual_triggers)
                if is_factual:
                    log.info("Knowledge sin datos factuales, fallback a research web...")
                    research_agent = get_agent("research")
                    if research_agent:
                        response = research_agent.handle(
                            {
                                "domain": "research",
                                "intent": "web_search",
                                "query": classification.get("query") or original_message,
                                "confidence": 0.0,
                            },
                            original_message,
                        )

        try:
            from core.proactive import log_action

            log_action(action=classification.get("intent", "unknown"), domain=domain, params=classification)
        except Exception as e:
            log.debug("log_action error: %s", e)

        return {"message": response, "domain": domain, "action": classification.get("intent", "none"), "classification": classification}
    except Exception as e:
        log.error("Error en %s: %s. Fallback a chat.", domain, e)
        chat_agent = get_agent("chat")
        if chat_agent is None:
            return {"message": "Error interno", "domain": "error", "action": "fallback"}
        response = chat_agent.handle(
            {"domain": "chat", "intent": "fallback", "query": original_message, "confidence": 0.0},
            original_message,
            on_token=on_token,
        )
        return {"message": response, "domain": "chat", "action": "fallback", "classification": classification}
