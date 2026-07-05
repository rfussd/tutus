from __future__ import annotations

import requests

from agents.base_agent import BaseAgent
from core.config import LM_STUDIO_URL, MODEL_ID


class DocsAgent(BaseAgent):
    name = "DocsAgent"
    domain = "docs"
    system_prompt = """Eres el agente de documentos de TUTUS.
Tu trabajo es decidir qué tipo de documento crear y con qué filename.

Acciones disponibles:
{
    "action": "create_word",
    "params": {"filename": "nombre", "topic": "tema del documento"},
    "message": "texto"
}
{
    "action": "create_excel",
    "params": {"filename": "nombre", "topic": "tema de la hoja"},
    "message": "texto"
}
{
    "action": "create_pdf",
    "params": {"filename": "nombre", "topic": "tema"},
    "message": "texto"
}
{
    "action": "create_pptx",
    "params": {"filename": "nombre", "topic": "tema", "slides": 5},
    "message": "texto"
}

Ejemplos:
- "crea un word sobre IA" → create_word filename="Inteligencia Artificial" topic="Inteligencia Artificial"
- "presentación de Python" → create_pptx filename="Python" topic="Python" slides=5
- "excel de gastos" → create_excel filename="Gastos Mensuales" topic="control de gastos mensuales"
- "pdf de resumen de machine learning" → create_pdf filename="Machine Learning" topic="Machine Learning" """

    def load_skills(self) -> None:
        self.skills = {
            "create_word": self._word_with_ai,
            "create_excel": self._excel_with_ai,
            "create_pdf": self._pdf_with_ai,
            "create_pptx": self._pptx_with_ai,
        }

    def _generate_content(self, prompt: str) -> str:
        """Genera contenido real con el LLM."""
        try:
            response = requests.post(
                LM_STUDIO_URL,
                json={
                    "model": MODEL_ID,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Eres un experto generando contenido estructurado. Responde SOLO con el contenido pedido, sin explicaciones adicionales.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2048,
                    "stream": False,
                },
                timeout=120,
            )
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()  # type: ignore[no-any-return]
        except Exception as e:
            return f"Error generando contenido: {str(e)}"

    def _pptx_with_ai(self, filename: str, topic: str, slides: int = 5) -> str:
        from skills.documents_skill import create_pptx

        prompt = f"""Crea contenido para una presentación de {slides} slides sobre: {topic}

Formato EXACTO para cada slide (una por línea):
Título de la slide|Punto 1 sobre el tema · Punto 2 importante · Punto 3 clave · Punto 4 relevante

REGLAS:
- Primera línea = slide de introducción
- Última línea = slide de conclusiones
- Usa · para separar puntos dentro de una slide
- Contenido concreto, no genérico
- En español
- SOLO el contenido, nada más

Genera exactamente {slides} líneas."""

        content = self._generate_content(prompt)
        return create_pptx(filename, content)

    def _word_with_ai(self, filename: str, topic: str) -> str:
        from skills.documents_skill import create_word

        prompt = f"""Escribe un documento profesional completo sobre: {topic}

ESTRUCTURA:
- Introducción clara
- 3-4 secciones principales con contenido detallado
- Conclusión
- En español, tono profesional
- Mínimo 400 palabras

SOLO el contenido del documento, sin títulos de sección marcados con # o **, solo texto plano con saltos de línea."""

        content = self._generate_content(prompt)
        return create_word(filename, content)

    def _excel_with_ai(self, filename: str, topic: str) -> str:
        from skills.documents_skill import create_excel

        prompt = f"""Crea datos para una hoja de Excel sobre: {topic}

FORMATO: CSV con comas, primera fila = headers, mínimo 8 filas de datos reales.
SOLO el CSV, sin explicaciones, sin backticks.

Ejemplo de formato:
Concepto,Enero,Febrero,Marzo,Total
Renta,8000,8000,8000,24000"""

        content = self._generate_content(prompt)
        return create_excel(filename, content)

    def _pdf_with_ai(self, filename: str, topic: str) -> str:
        from skills.documents_skill import create_pdf

        prompt = f"""Escribe un documento PDF profesional sobre: {topic}

ESTRUCTURA:
- Título y subtítulo
- Introducción
- Desarrollo en 3-4 secciones
- Conclusiones
- En español, tono formal
- Mínimo 500 palabras
- SOLO texto plano con saltos de línea, sin markdown"""

        content = self._generate_content(prompt)
        return create_pdf(filename, content)
