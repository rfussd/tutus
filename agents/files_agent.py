from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from core.memory_signals import set_signal


class FilesAgent(BaseAgent):
    name = "FilesAgent"
    domain = "files"
    system_prompt = """Eres el agente de archivos de TUTUS.
Tu trabajo es organizar, mover y listar archivos de David.

Acciones disponibles:
{
    "action": "organize_downloads",
    "params": {},
    "message": "texto"
}
{
    "action": "list_files",
    "params": {"folder": "descargas/escritorio/documentos"},
    "message": "texto"
}
{
    "action": "move_file",
    "params": {"filename": "archivo.pdf", "destination": "documentos"},
    "message": "texto"
}

Carpetas permitidas: descargas, escritorio, documentos, música, imágenes, videos.

Ejemplos:
- "organiza mis descargas" → organize_downloads
- "qué hay en el escritorio" → list_files con folder "escritorio"
- "mueve mi cv a documentos" → move_file con filename y destination"""

    def load_skills(self) -> None:
        from skills.files_skill import list_files, move_file, organize_downloads

        self.skills = {
            "organize_downloads": organize_downloads,
            "list_files": list_files,
            "move_file": move_file,
        }

    def _learn(self, classification: dict[str, Any], decision: dict[str, Any], original_message: str = "") -> None:
        action = decision.get("action", "")
        params = decision.get("params", {})

        if action == "organize_downloads":
            from datetime import datetime

            set_signal(self.domain, "last_organized", datetime.now().isoformat())

        if action == "list_files":
            folder = params.get("folder", "")
            if folder:
                frequent = self.get_signal_safe("frequent_folders", [])
                if folder not in frequent:
                    frequent.insert(0, folder)
                    set_signal(self.domain, "frequent_folders", frequent[:5])

    def get_signal_safe(self, key: str, default: Any = None) -> Any:
        from core.memory_signals import get_signal

        return get_signal(self.domain, key, default)
