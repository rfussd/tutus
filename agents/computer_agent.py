from __future__ import annotations

from agents.base_agent import StepwiseTaskAgent

COMPUTER_PROMPT = """Controlas el PC de David con screenshots. Una accion por respuesta.

Acciones: click, double_click, right_click, type, press, hotkey, scroll, wait, done

{"action":"click","params":{"x":500,"y":300}}
{"action":"type","params":{"text":"hola"}}
{"action":"press","params":{"key":"enter"}}
{"action":"hotkey","params":{"keys":["ctrl","c"]}}
{"action":"done","params":{"message":"completado"}}"""


class ComputerAgent(StepwiseTaskAgent):
    name = "ComputerAgent"
    domain = "computer"
    system_prompt = COMPUTER_PROMPT
    max_steps = 15
    task_timeout = 60

    def load_skills(self) -> None:
        from skills.computer_skill import (
            capture_screen_base64,
            click,
            double_click,
            get_screen_size,
            hotkey,
            press_key,
            right_click,
            scroll,
            type_text,
            wait,
        )

        self.skills = {
            "click": click,
            "double_click": double_click,
            "right_click": right_click,
            "type": type_text,
            "press": press_key,
            "hotkey": hotkey,
            "scroll": scroll,
            "wait": wait,
        }
        self._screenshot_fn = capture_screen_base64
        self._screen_size = get_screen_size

    def _get_extra_images(self) -> list[str]:
        return [self._screenshot_fn()]

    def _build_user_message(self, task: str, step: int, history: str) -> str:
        screen_info = self._screen_size()
        return f"""Paso {step}/{self.max_steps}
Tarea: {task}
Pantalla: {screen_info}
{history}

¿Cuál es la siguiente acción? Responde SOLO con JSON."""
