from __future__ import annotations

from agents.base_agent import BaseAgent


class VisionAgent(BaseAgent):
    name = "VisionAgent"
    domain = "vision"
    system_prompt = """Eres el agente de visión de TUTUS.
Tu trabajo es analizar la pantalla de David y responder preguntas sobre lo que ve.

Acciones disponibles:
{
    "action": "analyze_screen",
    "params": {"question": "pregunta específica sobre la pantalla"},
    "message": "texto"
}
{
    "action": "screenshot",
    "params": {"filename": "nombre_archivo"},
    "message": "texto"
}

Ejemplos:
- "qué hay en mi pantalla" → analyze_screen con question genérica
- "ayúdame con esto de la pantalla" → analyze_screen con question sobre contexto
- "qué configuración es esta" → analyze_screen preguntando sobre config
- "guarda una captura" → screenshot con filename"""

    def load_skills(self) -> None:
        from skills.vision_skill import analyze_screen, take_screenshot

        self.skills = {
            "analyze_screen": analyze_screen,
            "screenshot": take_screenshot,
        }
