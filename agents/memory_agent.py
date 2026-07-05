from __future__ import annotations

from agents.base_agent import BaseAgent


class MemoryAgent(BaseAgent):
    name = "MemoryAgent"
    domain = "memory"
    system_prompt = """Eres el agente de memoria de TUTUS.
Tu trabajo es guardar, buscar y olvidar información de David.

Acciones disponibles:
{
    "action": "save_memory",
    "params": {"content": "contenido", "domain": "dominio", "category": "categoría"},
    "message": "texto"
}
{
    "action": "search_memory",
    "params": {"query": "búsqueda", "domain": "dominio o null"},
    "message": "texto"
}
{
    "action": "forget_memory",
    "params": {"query": "qué olvidar", "domain": "dominio o null"},
    "message": "texto"
}
{
    "action": "list_memories",
    "params": {"domain": "dominio o null"},
    "message": "texto"
}

Dominios: music, files, docs, system, vision, windows, general

Ejemplos:
- "recuerda que me gusta Jose Jose" → save_memory domain=music
- "recuerda que tengo clase el viernes" → save_memory domain=general category=tarea
- "qué recuerdas de mí" → search_memory query="" domain=null
- "olvida lo del examen" → forget_memory query="examen"
- "qué recuerdas de música" → search_memory domain=music"""

    def load_skills(self) -> None:
        from skills.memory_skill import forget_memory, list_memories, save_memory, search_memory

        self.skills = {
            "save_memory": save_memory,
            "search_memory": search_memory,
            "forget_memory": forget_memory,
            "list_memories": list_memories,
        }
