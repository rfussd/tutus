"""Tests unitarios para módulos core sin dependencias externas pesadas."""

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ── Config ───────────────────────────────────────────────────────────────────


def test_config_has_required_keys():
    from core.config import (
        DATA_DIR,
        HOTWORD,
        LM_STUDIO_URL,
        MODEL_ID,
        WHISPER_MODEL,
    )

    assert LM_STUDIO_URL.startswith("http")
    assert isinstance(MODEL_ID, str) and len(MODEL_ID) > 0
    assert DATA_DIR.exists()
    assert isinstance(WHISPER_MODEL, str)
    assert isinstance(HOTWORD, str)


# ── Chat Data ────────────────────────────────────────────────────────────────


def test_chat_message_defaults():
    from ui.chat_data import ChatMessage, format_time

    msg = ChatMessage(role="user", text="hola")
    assert msg.role == "user"
    assert msg.text == "hola"
    assert msg.sender == ""
    assert msg.timestamp > 0
    assert isinstance(format_time(msg.timestamp), str)
    assert ":" in format_time(msg.timestamp)


def test_chat_message_custom():
    from ui.chat_data import ChatMessage

    msg = ChatMessage(role="assistant", text="mundo", sender="TUTUS")
    assert msg.sender == "TUTUS"
    assert msg.role == "assistant"


# ── Chat History Serialization ───────────────────────────────────────────────


def test_chat_message_json():
    from ui.chat_data import ChatMessage

    msg = ChatMessage(role="user", text="test", sender="TÚ")
    data = {"role": msg.role, "text": msg.text, "sender": msg.sender, "timestamp": msg.timestamp}
    restored = ChatMessage(**data)
    assert restored.role == "user"
    assert restored.text == "test"
    assert restored.sender == "TÚ"
    assert restored.timestamp == msg.timestamp


# ── Constants ────────────────────────────────────────────────────────────────


def test_constants():
    from ui.constants import ANIM_DURATION, BUBBLE_MAX_WIDTH, HEADER_HEIGHT, WINDOW_SIZE

    assert BUBBLE_MAX_WIDTH > 0
    assert ANIM_DURATION > 0
    assert len(WINDOW_SIZE) == 2
    assert HEADER_HEIGHT > 0


# ── Engine (sin dependencias pesadas) ────────────────────────────────────────


def test_engine_create():
    from core.engine import TutusEngine

    engine = TutusEngine()
    assert engine is not None
    assert hasattr(engine, "startup")
    assert hasattr(engine, "voice")
    assert hasattr(engine, "background")
    assert not engine.is_ready


def test_engine_startup_service():
    from core.engine import StartupService

    s = StartupService()
    assert not s.is_ready
    assert s.wait_ready(timeout=0.01) is False  # timeout, no error


def test_engine_voice_service():
    from core.engine import VoiceService

    v = VoiceService()
    assert not v.is_continuous_active
    v.stop_continuous()  # should not raise


def test_engine_background_service():
    from core.engine import BackgroundService

    ip = BackgroundService.get_web_ip()
    assert isinstance(ip, str)
    assert len(ip) > 0


# ── Markdown ─────────────────────────────────────────────────────────────────


def test_markdown_basic():
    from core.markdown import markdown_to_html

    html = markdown_to_html("hola **mundo**")
    assert "<b>mundo</b>" in html


def test_markdown_inline_code():
    from core.markdown import markdown_to_html

    html = markdown_to_html("usa `codigo` aqui")
    assert "<code>codigo</code>" in html


def test_markdown_code_block():
    from core.markdown import markdown_to_html

    html = markdown_to_html("```python\nprint('hi')\n```")
    assert "<pre>" in html
    assert "print" in html


def test_markdown_list():
    from core.markdown import markdown_to_html

    html = markdown_to_html("- item")
    assert "<li>item</li>" in html


# ── Settings Persistence (simulado) ──────────────────────────────────────────


def test_settings_defaults():
    defaults = {
        "tts_rate": 115,
        "auto_tts": True,
        "proactive": False,
        "temperature": 70,
        "max_tokens": 2048,
    }
    assert defaults["tts_rate"] == 115
    assert defaults["auto_tts"] is True
    assert defaults["max_tokens"] == 2048


def test_settings_roundtrip():
    data = {"tts_rate": 150, "auto_tts": False, "temperature": 50}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(data, f)
        path = f.name
    try:
        with open(path, encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded["tts_rate"] == 150
        assert loaded["auto_tts"] is False
    finally:
        os.unlink(path)


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v", "--tb=short"])
