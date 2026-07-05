# TUTUS — Asistente Personal con IA

[![CI](https://github.com/dan/tutus/actions/workflows/test.yml/badge.svg)](https://github.com/dan/tutus/actions/workflows/test.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-000000)](https://github.com/astral-sh/ruff)
[![Mypy](https://img.shields.io/badge/mypy-strict-2a6db0)](https://mypy-lang.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-178%2B%20passing-brightgreen)]()
[![Coverage](https://img.shields.io/badge/coverage-85%25-yellowgreen)]()

TUTUS es un asistente personal con IA que vive en tu PC. Conversa, controla tu computadora, busca en internet, ejecuta código, reproduce música y aprende de ti — todo local con LM Studio.

## Arquitectura

```
┌─────────────────────────────────────┐
│           UI (PyQt6)                │
│  ┌─────────┐ ┌───────────────────┐  │
│  │  Avatar  │ │    Chat Panel     │  │
│  └─────────┘ └───────────────────┘  │
│  ┌──────────────────────────────┐   │
│  │       Settings Panel         │   │
│  └──────────────────────────────┘   │
└──────────────┬──────────────────────┘
               │ signals / slots
┌──────────────▼──────────────────────┐
│         TutusEngine (facade)        │
│  ┌─────────┐ ┌──────────┐ ┌──────┐ │
│  │ Startup │ │  Voice   │ │ BG   │ │
│  │ Service │ │ Service  │ │ Svc  │ │
│  └─────────┘ └──────────┘ └──────┘ │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│         Orchestrator                │
│  ┌─────────────┐ ┌───────────────┐  │
│  │  classify() │ │agent_router() │  │
│  └─────────────┘ └───────┬───────┘  │
└──────────────────────────┼──────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  ChatAgent   │  │ ResearchAgent│  │ ComputerAgent│
│  (gato TUTUS)│  │ (web search) │  │ (PC control) │
└──────────────┘  └──────────────┘  └──────────────┘
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ KnowledgeAgent│  │ ProjectAgent │  │ BrowserAgent │
│ (grafos)     │  │  (código)    │  │ (navegador)  │
└──────────────┘  └──────────────┘  └──────────────┘
```

## Stack

| Capa       | Tecnología                          |
|------------|-------------------------------------|
| UI         | PyQt6 + QSS (glassmorphism)         |
| LLM        | LM Studio (local, API `:1234/v1`)   |
| Voz        | Whisper (STT) + edge-tts (TTS)      |
| Memoria    | SQLite FTS5 + Knowledge Graph       |
| RAG        | ChromaDB + Sentence Transformers    |
| Sandbox    | AST analysis, 17 módulos bloqueados |
| Tests      | pytest + monkeypatch                |
| CI/CD      | GitHub Actions (ruff + pytest)      |

## Quickstart

```bash
# 1. Clonar
git clone https://github.com/dan/tutus.git
cd tutus

# 2. Instalar (producción)
pip install -e .

# 3. Instalar (desarrollo — incluye ruff, mypy, pytest)
pip install -e ".[dev]"

# 4. Iniciar LM Studio (servidor en :1234)
lms server start

# 5. Ejecutar
tutus
```

### Makefile

```bash
make install     # pip install -e .
make run         # tutus
make test        # pytest -v --tb=short
make test-cov    # pytest --cov=core --cov=agents --cov=skills
make lint        # ruff check .
make format      # ruff format .
make typecheck   # mypy .
make clean       # clean __pycache__ / .pytest_cache
make precommit   # pre-commit run --all-files
```

## Tests

```bash
pytest -v                          # ~190+ tests, 0 fail
pytest --cov=core --cov=agents --cov=skills  # con cobertura
pytest tests/test_ui.py -v         # solo UI (requiere PyQt6)
```

| Tipo               | Archivos                          | Cantidad |
|--------------------|-----------------------------------|----------|
| Unitarios          | `test_*.py` (core)                | ~80      |
| E2E / Integración  | `test_e2e.py`, `test_integration.py` | ~60   |
| UI (offscreen)     | `test_ui.py`                      | ~15      |
| Agentes            | `test_*_agent.py`                 | ~30      |

## Agentes

| Agente         | Dominio     | Función                          |
|----------------|-------------|----------------------------------|
| ChatAgent      | `chat`      | Conversación con personalidad    |
| MusicAgent     | `music`     | Reproducir música (Spotify)      |
| SystemAgent    | `system`    | Abrir apps, navegador            |
| ComputerAgent  | `computer`  | Controlar mouse/teclado/pantalla |
| BrowserAgent   | `browser`   | Automatización de navegador      |
| ResearchAgent  | `research`  | Buscar en internet               |
| KnowledgeAgent | `knowledge` | Grafo de conocimiento personal   |
| ProjectAgent   | `dev`       | Leer/escribir archivos, shell    |
| CodeAgent      | `code`      | Ejecutar Python sandboxeado      |
| ReminderAgent  | `reminder`  | Recordatorios                    |
| VisionAgent    | `vision`    | Captura y análisis de pantalla   |

## Clasificación

TUTUS usa un pipeline de 2 capas:

1. **Pre-clasificación** (regex, sin LLM): saludos, identidad, opiniones → chat directo
2. **LLM** (orchestrator → LM Studio): el resto de dominios

El fallback seguro es siempre `chat` — cualquier error o ambigüedad termina en conversación natural.

## Licencia

MIT
