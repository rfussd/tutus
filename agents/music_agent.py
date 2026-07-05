from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from core.memory_signals import get_signal, set_signal


class MusicAgent(BaseAgent):
    name = "MusicAgent"
    domain = "music"
    system_prompt = """Eres el agente de música de TUTUS.
Tu trabajo es decidir cómo reproducir música para David.

REGLAS:
- Si no especifica plataforma, usa la preferida (señal: preferred_platform)
- Si no hay preferencia, usa Spotify por default
- "video" o "youtube" explícito → YouTube
- Todo lo demás → Spotify
- Si no hay query, usa los artistas favoritos de la memoria

Acciones disponibles:
{
    "action": "spotify_play",
    "params": {"query": "artista o canción"},
    "message": "texto para David"
}
{
    "action": "spotify_pause",
    "params": {},
    "message": "texto"
}
{
    "action": "spotify_next",
    "params": {},
    "message": "texto"
}
{
    "action": "spotify_previous",
    "params": {},
    "message": "texto"
}
{
    "action": "spotify_volume",
    "params": {"volume": 0-100},
    "message": "texto"
}
{
    "action": "spotify_playlist",
    "params": {"query": "nombre playlist"},
    "message": "texto"
}
{
    "action": "youtube_play",
    "params": {"query": "video a buscar"},
    "message": "texto"
}

Ejemplos:
- "pon jose jose" → spotify_play con query "Jose Jose"
- "y si pones algo de música" → spotify_play con artista favorito de memoria
- "pon el video de bad bunny" → youtube_play
- "sube el volumen" → spotify_volume con volume 80
- "pausa" → spotify_pause
- "siguiente" → spotify_next"""

    def load_skills(self) -> None:
        from skills.spotify_skill import (
            spotify_next,
            spotify_pause,
            spotify_play,
            spotify_playlist,
            spotify_previous,
            spotify_volume,
        )
        from skills.youtube_skill import youtube_play

        self.skills = {
            "spotify_play": spotify_play,
            "spotify_pause": spotify_pause,
            "spotify_next": spotify_next,
            "spotify_previous": spotify_previous,
            "spotify_volume": spotify_volume,
            "spotify_playlist": spotify_playlist,
            "youtube_play": youtube_play,
        }

    def _learn(self, classification: dict[str, Any], decision: dict[str, Any], original_message: str = "") -> None:
        action = decision.get("action", "")
        params = decision.get("params", {})

        # Aprender plataforma preferida
        if "spotify" in action:
            set_signal(self.domain, "preferred_platform", "spotify")
        elif "youtube" in action:
            set_signal(self.domain, "preferred_platform", "youtube")

        # Aprender artistas recientes
        query = params.get("query")
        if query and "play" in action:
            recent = get_signal(self.domain, "recent_artists", [])
            if query not in recent:
                recent.insert(0, query)
                set_signal(self.domain, "recent_artists", recent[:5])
