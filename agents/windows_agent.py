from __future__ import annotations

from agents.base_agent import BaseAgent


class WindowsAgent(BaseAgent):
    name = "WindowsAgent"
    domain = "windows"
    system_prompt = """Eres el agente de control de ventanas de TUTUS.
Tu trabajo es minimizar, maximizar, cerrar, mover y lanzar ventanas en Windows.

Acciones disponibles:
{"action":"launch","params":{"app":"nombre_app"},"message":"texto"}
{"action":"minimize_window","params":{"app":"nombre_app"},"message":"texto"}
{"action":"maximize_window","params":{"app":"nombre_app"},"message":"texto"}
{"action":"close_window","params":{"app":"nombre_app"},"message":"texto"}
{"action":"focus_window","params":{"app":"nombre_app"},"message":"texto"}
{"action":"move_window","params":{"app":"nombre_app","position":"left/right/center/fullscreen"},"message":"texto"}
{"action":"list_windows","params":{},"message":"texto"}

Ejemplos:
- "abre spotify" → launch con app "spotify"
- "abre chrome" → launch con app "chrome"
- "minimiza spotify" → minimize_window con app "spotify"
- "cierra chrome" → close_window con app "chrome"
- "pon spotify a la derecha" → move_window con position "right"
- "maximiza vs code" → maximize_window con app "vs code"
- "qué ventanas tengo abiertas" → list_windows"""

    def load_skills(self) -> None:
        from skills.window_control_skill import (
            close_window,
            focus_window,
            list_windows,
            maximize_window,
            minimize_window,
            move_window,
        )

        self.skills = {
            "launch": self._launch_app,
            "minimize_window": minimize_window,
            "maximize_window": maximize_window,
            "close_window": close_window,
            "focus_window": focus_window,
            "move_window": move_window,
            "list_windows": list_windows,
        }

    def _launch_app(self, app: str) -> str:
        import subprocess

        try:
            subprocess.Popen(["cmd", "/c", "start", app])
            return f"Lanzando {app}..."
        except Exception as e:
            return f"Error al lanzar {app}: {e}"
