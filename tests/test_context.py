import pytest

from tests.helpers import MockResponse


@pytest.fixture(autouse=True)
def reset_context(monkeypatch):
    import core.context

    core.context._conversation_summary = ""

    import core.conversation

    core.conversation._conversation_buffer.clear()

    yield

    core.context._conversation_summary = ""
    core.conversation._conversation_buffer.clear()


@pytest.fixture
def mock_context_lmstudio(monkeypatch):
    def mock_post(url, **kwargs):
        return MockResponse(json_data={"choices": [{"message": {"content": "El usuario saludo y pregunto por el clima."}}]})

    monkeypatch.setattr("requests.post", mock_post)


class TestSummarizeConversation:
    def test_summarize_with_empty_buffer(self):
        from core.context import get_summary, summarize_conversation

        summarize_conversation()
        assert get_summary() == ""

    def test_summarize_with_messages(self, mock_context_lmstudio):
        from core.context import get_summary, summarize_conversation
        from core.conversation import add_to_buffer

        add_to_buffer("user", "hola")
        add_to_buffer("assistant", "hola que tal")
        summarize_conversation()
        assert get_summary() != ""
        assert "saludo" in get_summary().lower() or "clima" in get_summary().lower()

    def test_summarize_strips_think_tags(self, monkeypatch):
        def mock_post(url, **kwargs):
            return MockResponse(json_data={"choices": [{"message": {"content": "<think>thinking</think>Resumen de prueba."}}]})

        monkeypatch.setattr("requests.post", mock_post)

        from core.context import get_summary, summarize_conversation
        from core.conversation import add_to_buffer

        add_to_buffer("user", "mensaje de prueba")
        summarize_conversation()
        summary = get_summary()
        assert "<think>" not in summary

    def test_summarize_api_error_does_not_crash(self, monkeypatch):
        def mock_post(url, **kwargs):
            raise Exception("API error")

        monkeypatch.setattr("requests.post", mock_post)

        from core.context import get_summary, summarize_conversation
        from core.conversation import add_to_buffer

        add_to_buffer("user", "test")
        summarize_conversation()
        assert get_summary() == ""


class TestAutoSummarizeIfNeeded:
    def test_below_threshold_no_summary(self, monkeypatch):
        monkeypatch.setattr("core.context.CONTEXT_SUMMARY_THRESHOLD", 10)

        from core.context import auto_summarize_if_needed, get_summary
        from core.conversation import add_to_buffer

        for i in range(5):
            add_to_buffer("user", f"msg {i}")
            add_to_buffer("assistant", f"resp {i}")
        auto_summarize_if_needed()
        assert get_summary() == ""

    def test_above_threshold_triggers_summary(self, monkeypatch):
        monkeypatch.setattr("core.context.CONTEXT_SUMMARY_THRESHOLD", 2)

        def mock_post(url, **kwargs):
            return MockResponse(json_data={"choices": [{"message": {"content": "Resumen de la conversacion."}}]})

        monkeypatch.setattr("requests.post", mock_post)

        from core.context import auto_summarize_if_needed, get_summary
        from core.conversation import add_to_buffer, get_buffer

        for i in range(3):
            add_to_buffer("user", f"msg {i}")
            add_to_buffer("assistant", f"resp {i}")
        auto_summarize_if_needed()
        assert get_summary() != ""
        assert len(get_buffer()) == 5
