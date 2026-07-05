from __future__ import annotations

"""
Modelos Pydantic para validación estricta de respuestas del LLM.
Evita errores silenciosos por JSON malformado o campos inesperados.
"""
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────
# Clasificación del orquestador
# ─────────────────────────────────────────
class Classification(BaseModel):
    """Resultado de orchestrator.classify()"""

    domain: Literal[
        "music",
        "files",
        "docs",
        "system",
        "vision",
        "windows",
        "memory",
        "chat",
        "research",
        "code",
        "reminder",
        "computer",
        "knowledge",
        "dev",
        "browser",
    ] = Field(description="Dominio de la intención")
    intent: str = Field(description="Acción principal en 2-3 palabras", min_length=1)
    query: str | None = Field(default=None, description="Término de búsqueda o parámetro principal")
    platform: Literal["spotify", "youtube"] | None = Field(default=None, description="Solo para domain=music")
    confidence: float = Field(ge=0.0, le=1.0, description="Confianza 0-1")

    @field_validator("query", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: Any) -> Any:  # noqa: N804
        if v == "" or v == "null":
            return None
        return v

    @field_validator("platform", mode="before")
    @classmethod
    def empty_platform_to_none(cls, v: Any) -> Any:
        if v == "" or v == "null":
            return None
        return v


# ─────────────────────────────────────────
# Decisión del agente (think)
# ─────────────────────────────────────────
class AgentDecision(BaseModel):
    """Resultado de BaseAgent.think() — qué action ejecutar"""

    action: str = Field(description="Nombre de la skill a ejecutar", min_length=1)
    params: dict[str, Any] = Field(default_factory=dict, description="Parámetros de la skill")
    message: str = Field(default="", description="Texto para el usuario")

    @field_validator("action", mode="before")
    @classmethod
    def none_to_str(cls, v: Any) -> Any:
        if v is None or v == "null":
            return "none"
        return v


# ─────────────────────────────────────────
# Resultado de ejecución (executor/skills)
# ─────────────────────────────────────────
class ActionResult(BaseModel):
    """Resultado unificado de ejecutar una acción"""

    success: bool = Field(description="Si la acción tuvo éxito")
    message: str = Field(default="", description="Mensaje para el usuario")
    data: dict[str, Any] | None = Field(default=None, description="Datos extra opcionales")
    error: str | None = Field(default=None, description="Error si success=False")


# ─────────────────────────────────────────
# Respuesta completa del router
# ─────────────────────────────────────────
class RouterResponse(BaseModel):
    """Respuesta final que devuelve agent_router.route() a la UI"""

    message: str | None = Field(default=None, description="Mensaje para mostrar al usuario")
    domain: str = Field(description="Dominio procesado")
    action: str = Field(default="none", description="Acción ejecutada")
    classification: Classification = Field(description="Clasificación original")
    success: bool = Field(default=True, description="Si todo fue bien")
    error: str | None = Field(default=None, description="Error si falló")


# ─────────────────────────────────────────
# Helpers de validación
# ─────────────────────────────────────────
def _extract_json(text: str) -> str:
    """Extrae el primer objeto JSON válido manejando braces anidados."""
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start != -1:
                return text[start : i + 1]
    raise ValueError("No se encontró JSON válido")


def parse_classification(raw_json: str) -> Classification:
    """Parsea y valida JSON del orquestador"""
    import json
    import re

    json_str = _extract_json(raw_json)
    json_str = re.sub(r':\s*"null"', ": null", json_str)
    json_str = re.sub(r":\s*none(?=[,\s}])", ": null", json_str)

    data = json.loads(json_str)
    return Classification(**data)


def parse_agent_decision(raw_json: str) -> AgentDecision:
    """Parsea y valida JSON de decisión de agente"""
    import json
    import re

    json_str = _extract_json(raw_json)
    json_str = re.sub(r':\s*"null"', ": null", json_str)
    json_str = re.sub(r":\s*none(?=[,\s}])", ": null", json_str)
    json_str = re.sub(r'(?<=: ")(.*?)(?=")', lambda m: m.group(0).replace("\n", "\\n"), json_str, flags=re.DOTALL)

    data = json.loads(json_str)
    return AgentDecision(**data)
