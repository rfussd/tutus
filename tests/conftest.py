import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


import pytest

from tests.helpers import MockResponse

SAMPLE_CLASSIFY_JSON = json.dumps(
    {
        "domain": "chat",
        "intent": "greet",
        "query": "hola",
        "platform": None,
        "confidence": 0.99,
    }
)

SAMPLE_DECISION_JSON = json.dumps(
    {
        "action": "none",
        "params": {},
        "message": "Hola, ¿en qué te ayudo?",
    }
)

SAMPLE_CLASSIFY_MUSIC = json.dumps(
    {
        "domain": "music",
        "intent": "play",
        "query": "jose jose",
        "platform": None,
        "confidence": 0.95,
    }
)


@pytest.fixture
def mock_lmstudio(monkeypatch):
    """Mockea requests.post para simular LM Studio."""

    response_map = {}

    def mock_post(url, **kwargs):
        if url in response_map:
            val = response_map[url]
            if callable(val):
                return val(url, **kwargs)
            elif isinstance(val, list):
                return val.pop(0)
            return val
        return MockResponse()

    monkeypatch.setattr("requests.post", mock_post)
    return response_map


@pytest.fixture
def mock_lmstudio_classify(mock_lmstudio, monkeypatch):
    """Mockea LM Studio para que classify() devuelva chat."""
    from core.config import LM_STUDIO_URL

    def set_response(json_str: str):
        mock_lmstudio[LM_STUDIO_URL] = MockResponse(json_data={"choices": [{"message": {"content": json_str}}]})

    set_response(SAMPLE_CLASSIFY_JSON)
    return set_response


@pytest.fixture
def temp_db(monkeypatch):
    """Crea DB temporal para memory_signals. Cada test obtiene DB limpia."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_path = Path(tmp.name)

    monkeypatch.setattr("core.memory_signals.DB_PATH", db_path)

    import core.memory_signals as ms

    ms._connection = None
    ms.init_db()

    yield db_path

    try:
        os.unlink(str(db_path))
    except Exception:
        pass


@pytest.fixture
def mock_streamer(monkeypatch):
    """Mockea core.streamer para evitar llamadas reales a LM Studio."""

    def mock_stream_chat(messages, **kwargs):
        on_token = kwargs.get("on_token")
        text = "Esto es una respuesta mockeada."
        if on_token:
            for word in text.split():
                on_token(word + " ")
        return text

    monkeypatch.setattr("core.streamer.stream_chat", mock_stream_chat)
    return mock_stream_chat
