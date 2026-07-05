from __future__ import annotations

import logging
from typing import Any

from agents.base_agent import BaseAgent

log = logging.getLogger("tutus.research_agent")


class ResearchAgent(BaseAgent):
    name = "ResearchAgent"
    domain = "research"
    system_prompt = """Eres el agente de investigación de TUTUS.
Tu trabajo es buscar información en la web y en documentos indexados.

Acciones disponibles:
{
    "action": "web_search",
    "params": {"query": "qué buscar"},
    "message": "texto para David"
}
{
    "action": "fetch_url",
    "params": {"url": "https://..."},
    "message": "texto"
}
{
    "action": "search_docs",
    "params": {"query": "qué buscar en documentos"},
    "message": "texto"
}
{
    "action": "index_file",
    "params": {"filepath": "ruta/al/archivo"},
    "message": "texto"
}
{
    "action": "index_all_docs",
    "params": {},
    "message": "texto"
}

Ejemplos:
- "investiga sobre inteligencia artificial" → web_search
- "busca en mis documentos sobre Python" → search_docs
- "indexa todos mis documentos" → index_all_docs"""

    def load_skills(self) -> None:
        from skills.rag_skill import buscar_en_documentos, indexar_archivo, indexar_documentos
        from skills.web_research_skill import fetch_url_content, search_and_summarize

        self.skills = {
            "web_search": search_and_summarize,
            "fetch_url": fetch_url_content,
            "search_docs": buscar_en_documentos,
            "index_file": indexar_archivo,
            "index_all_docs": indexar_documentos,
        }

    def think(self, classification: dict[str, Any], original_message: str, on_token: Any = None) -> dict[str, Any]:
        msg_lower = original_message.lower().strip()
        identity_tokens = [
            "quien eres",
            "quién eres",
            "como te llamas",
            "cómo te llamas",
            "que eres",
            "qué eres",
            "tu quien eres",
            "tú quién eres",
            "tutus",
            "como te llamas tu",
            "cómo te llamas tú",
        ]
        if any(t in msg_lower for t in identity_tokens):
            log.info("ResearchAgent detectó identidad, redirigiendo a chat")
            return {"action": "none", "params": {}, "message": ""}
        return super().think(classification, original_message, on_token=on_token)
