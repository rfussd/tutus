import pytest


@pytest.fixture(autouse=True)
def reset_buffer():
    import core.conversation

    core.conversation._conversation_buffer.clear()
    yield
    core.conversation._conversation_buffer.clear()


@pytest.fixture(autouse=True)
def mock_log_conversation(monkeypatch):
    monkeypatch.setattr("core.memory_signals.log_conversation", lambda *a, **kw: None)


class TestAddToBuffer:
    def test_add_message(self):
        from core.conversation import add_to_buffer, get_buffer

        add_to_buffer("user", "hola")
        buf = get_buffer()
        assert len(buf) == 1
        assert buf[0]["role"] == "user"
        assert buf[0]["content"] == "hola"

    def test_add_multiple_messages(self):
        from core.conversation import add_to_buffer, get_buffer

        add_to_buffer("user", "hola")
        add_to_buffer("assistant", "mundo")
        buf = get_buffer()
        assert len(buf) == 2

    def test_max_size_enforced(self):
        from core.conversation import add_to_buffer, get_buffer

        for i in range(10):
            add_to_buffer("user", f"msg {i}")
        buf = get_buffer()
        assert len(buf) <= 8

    def test_oldest_removed_when_full(self):
        from core.conversation import add_to_buffer, get_buffer

        for i in range(10):
            add_to_buffer("user", f"msg {i}")
        buf = get_buffer()
        contents = [m["content"] for m in buf]
        assert "msg 0" not in contents
        assert "msg 9" in contents

    def test_add_system_message(self):
        from core.conversation import add_to_buffer, get_buffer

        add_to_buffer("system", "[Resumen de la conversacion]")
        buf = get_buffer()
        assert buf[0]["role"] == "system"


class TestGetBuffer:
    def test_get_buffer_empty(self):
        from core.conversation import get_buffer

        assert get_buffer() == []

    def test_get_buffer_returns_list_of_dicts(self):
        from core.conversation import add_to_buffer, get_buffer

        add_to_buffer("user", "contenido")
        buf = get_buffer()
        assert isinstance(buf, list)
        assert isinstance(buf[0], dict)
        assert "role" in buf[0]
        assert "content" in buf[0]

    def test_get_buffer_returns_shared_list(self):
        from core.conversation import add_to_buffer, get_buffer

        add_to_buffer("user", "test")
        buf = get_buffer()
        buf.append({"role": "system", "content": "extra"})
        assert len(get_buffer()) == 2
