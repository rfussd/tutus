from __future__ import annotations

from agents.base_agent import BaseAgent


class CodeAgent(BaseAgent):
    name = "CodeAgent"
    domain = "code"
    system_prompt = """Eres el agente de código de TUTUS.
Tu trabajo es ejecutar código Python para David.

Acciones disponibles:
{
    "action": "run_python",
    "params": {"code": "código Python a ejecutar"},
    "message": "texto para David"
}

Ejemplos:
- "ejecuta print('hola')" → run_python con code="print('hola')"
- "ejecuta este código: suma = 2+2; print(suma)" → run_python con code
- "calcula la raíz cuadrada de 144" → run_python con código Python que calcule

El código se ejecuta en un sandbox seguro. No permitas imports peligrosos."""

    def load_skills(self) -> None:
        from skills.code_sandbox_skill import execute_python

        self.skills = {"run_python": execute_python}
