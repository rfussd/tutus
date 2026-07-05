from __future__ import annotations

from collections.abc import Callable
from typing import Any

from agents.base_agent import BaseAgent
from core.knowledge_graph import get_knowledge_graph


class KnowledgeAgent(BaseAgent):
    name = "KnowledgeAgent"
    domain = "knowledge"
    system_prompt = "Eres TUTUS Knowledge. Administras la memoria a largo plazo de TUTUS en forma de grafo de conocimiento."

    def load_skills(self) -> None:
        self._kg = get_knowledge_graph()

    def think(self, classification: dict[str, Any], original_message: str, on_token: Callable[[str], None] | None = None) -> dict[str, Any]:
        query = classification.get("query") or original_message
        intent = classification.get("intent", "query")
        kg = get_knowledge_graph()

        if intent == "learn":
            triples = kg.add_triples_from_text(query, use_llm=True)
            if triples:
                return {
                    "action": "respond",
                    "params": {},
                    "message": f"Aprendí {len(triples)} cosas nuevas:\n" + "\n".join(f"  • {t[0]} → {t[1]} → {t[2]}" for t in triples),
                }
            return {"action": "respond", "params": {}, "message": "No encontré hechos concretos para aprender."}

        if intent == "stats":
            return {"action": "respond", "params": {}, "message": kg.get_graph_insights()}

        if intent == "forget":
            return {"action": "respond", "params": {}, "message": "Función de olvidar no implementada aún."}

        entity = (
            query.replace("recuerdas", "")
            .replace("sabes de", "")
            .replace("quién es", "")
            .replace("qué es", "")
            .replace("dime de", "")
            .strip()
        )
        if not entity:
            return {"action": "respond", "params": {}, "message": kg.get_graph_insights()}
        info = kg.fmt_entity_info(entity)
        recent = kg.get_recent_context(entity, days=30)
        if recent:
            info += f"\n\nContexto reciente:\n{recent}"
        return {"action": "respond", "params": {}, "message": info}

    def execute(self, decision: dict[str, Any]) -> str:
        return decision.get("message", "")  # type: ignore[no-any-return]
