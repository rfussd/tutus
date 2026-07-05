from __future__ import annotations

from agents.base_agent import StepwiseTaskAgent

DEV_PROMPT = """Ayudas con codigo en proyecto TUTUS. Lee antes de editar, verifica syntax despues.

Herramientas:
read_file, write_file, edit_file, glob, grep, run_shell, check_syntax, get_file_tree, permit_path, deny_path, list_permitted

Reglas: lee antes de editar, verifica con check_syntax, divide tareas complejas, para acceso externo usa permit_path.

JSON respuesta:
{"action":"read_file","params":{"path":"core/config.py"}}
{"action":"edit_file","params":{"path":"x.py","old_string":"a","new_string":"b"}}
{"action":"done","params":{},"message":"que hice"}"""


class ProjectAgent(StepwiseTaskAgent):
    name = "ProjectAgent"
    domain = "dev"
    system_prompt = DEV_PROMPT
    max_steps = 20
    task_timeout = 90

    def load_skills(self) -> None:
        from skills.project_skill import (
            check_syntax,
            deny_path,
            edit_file,
            get_file_tree,
            glob,
            grep,
            list_permitted,
            permit_path,
            read_file,
            run_shell,
            write_file,
        )

        self.skills = {
            "read_file": read_file,
            "write_file": write_file,
            "edit_file": edit_file,
            "glob": glob,
            "grep": grep,
            "run_command": run_shell,
            "check_syntax": check_syntax,
            "get_file_tree": get_file_tree,
            "permit_path": permit_path,
            "deny_path": deny_path,
            "list_permitted": list_permitted,
        }

    def _build_user_message(self, task: str, step: int, history: str) -> str:
        return f"""Paso {step}/{self.max_steps}
Proyecto: TUTUS (asistente local AI con agentes)

Tarea original: {task}

Historial:
{history}

¿Cuál es la siguiente acción? Una sola acción. Responde SOLO con JSON."""
