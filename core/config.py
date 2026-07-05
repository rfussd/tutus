from __future__ import annotations

import os
from pathlib import Path

LM_STUDIO_URL: str = os.getenv("TUTUS_LM_STUDIO_URL", "http://127.0.0.1:1234/v1/chat/completions")
LM_STUDIO_BASE: str = LM_STUDIO_URL.replace("/v1/chat/completions", "").replace("/chat/completions", "").rstrip("/")
MODEL_ID: str = os.getenv("TUTUS_MODEL_ID", "qwen/qwen3-vl-8b")

TIMEOUT_CLASSIFY: int = int(os.getenv("TUTUS_TIMEOUT_CLASSIFY", "30"))
TIMEOUT_THINK: int = int(os.getenv("TUTUS_TIMEOUT_THINK", "60"))
TIMEOUT_CHAT: int = int(os.getenv("TUTUS_TIMEOUT_CHAT", "60"))

BASE_DIR: Path = Path(__file__).parent.parent
DATA_DIR: Path = BASE_DIR / "data"
MEMORY_JSON: Path = DATA_DIR / "memory.json"
MEMORY_DB: Path = DATA_DIR / "memory.db"
RAG_DB_DIR: Path = DATA_DIR / "rag_db"
PLUGINS_DIR: Path = BASE_DIR / "plugins"
DOCUMENTS_DIR: Path = DATA_DIR / "documents"

WHISPER_MODEL: str = os.getenv("TUTUS_WHISPER_MODEL", "base")
RECORD_DURATION: int = int(os.getenv("TUTUS_RECORD_DURATION", "5"))
SAMPLE_RATE: int = 16000

PROACTIVE_CHECK_INTERVAL_MIN: int = int(os.getenv("TUTUS_PROACTIVE_INTERVAL", "30"))
PATTERN_MIN_FREQUENCY: int = int(os.getenv("TUTUS_PATTERN_MIN_FREQ", "3"))
PATTERN_HOUR_TOLERANCE: int = int(os.getenv("TUTUS_PATTERN_HOUR_TOL", "1"))

WINDOW_WIDTH: int = 400
WINDOW_HEIGHT: int = 600
AVATAR_SIZE: int = 90

HOTWORD: str = os.getenv("TUTUS_HOTWORD", "tutus")
HOTWORD_SENSITIVITY: float = float(os.getenv("TUTUS_HOTWORD_SENSITIVITY", "0.5"))

EMBEDDING_MODEL: str = os.getenv("TUTUS_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
EMBEDDING_DIM: int = int(os.getenv("TUTUS_EMBEDDING_DIM", "384"))
CHUNK_SIZE: int = int(os.getenv("TUTUS_CHUNK_SIZE", "512"))
CHUNK_OVERLAP: int = int(os.getenv("TUTUS_CHUNK_OVERLAP", "64"))
RAG_TOP_K: int = int(os.getenv("TUTUS_RAG_TOP_K", "5"))

STREAMING_ENABLED: bool = os.getenv("TUTUS_STREAMING", "true").lower() == "true"
CONTEXT_SUMMARY_THRESHOLD: int = int(os.getenv("TUTUS_CONTEXT_SUMMARY_THRESHOLD", "6"))

LORA_ENABLED: bool = os.getenv("TUTUS_LORA_ENABLED", "false").lower() == "true"
LORA_ADAPTER_PATH: str = os.getenv("TUTUS_LORA_ADAPTER", str(BASE_DIR / "training" / "lora_adapter"))
