import core.orchestrator
from tests.helpers import MockResponse


class TestClassify:
    def test_classify_chat(self, mock_lmstudio_classify):
        from core.orchestrator import classify

        result = classify("hola")
        assert result["domain"] == "chat"
        assert result["intent"] == "greet"
        assert result["confidence"] == 0.99

    def test_classify_changes_response(self, mock_lmstudio_classify):
        from core.orchestrator import classify

        mock_lmstudio_classify('{"domain":"music","intent":"play","query":"jose jose","confidence":0.95}')
        result = classify("pon jose jose")
        assert result["domain"] == "music"
        assert result["query"] == "jose jose"

    def test_classify_http_error_fallback(self, mock_lmstudio):
        import requests

        from core.config import LM_STUDIO_URL

        def failing(url, **kwargs):
            raise requests.ConnectionError("No se pudo conectar")

        mock_lmstudio[LM_STUDIO_URL] = failing
        from core.orchestrator import classify

        result = classify("hola")
        assert result["domain"] == "chat"
        assert result["intent"] == "unknown"

    def test_classify_invalid_json_fallback(self, mock_lmstudio):
        from core.config import LM_STUDIO_URL

        def bad_json(url, **kwargs):
            return MockResponse(json_data={"choices": [{"message": {"content": "no json aqui"}}]})

        mock_lmstudio[LM_STUDIO_URL] = bad_json
        from core.orchestrator import classify

        result = classify("hola")
        assert result["domain"] == "chat"
        assert result["intent"] == "unknown"


class TestDetectMultiIntent:
    def test_single_intent(self):
        assert core.orchestrator.detect_multi_intent("hola") == []

    def test_two_intents_with_y(self):
        result = core.orchestrator.detect_multi_intent("abre spotify y pon música")
        assert len(result) >= 2

    def test_two_intents_with_comma(self):
        result = core.orchestrator.detect_multi_intent("abre spotify, pon música")
        assert len(result) >= 2

    def test_short_parts_filtered(self):
        assert core.orchestrator.detect_multi_intent("a y b") == []

    def test_empty_message(self):
        assert core.orchestrator.detect_multi_intent("") == []


class TestAddToBuffer:
    def test_add_and_buffer_size(self):
        from core.conversation import get_buffer

        get_buffer().clear()
        core.orchestrator.add_to_buffer("user", "hola")
        core.orchestrator.add_to_buffer("assistant", "hey")
        assert len(get_buffer()) >= 2
        assert get_buffer()[-1]["role"] == "assistant"

    def test_buffer_max_size(self):
        from core.conversation import get_buffer

        get_buffer().clear()
        for i in range(20):
            core.orchestrator.add_to_buffer("user", f"msg {i}")
        assert len(get_buffer()) <= 8


class TestRouteParallel:
    def test_parallel_routing(self, mock_lmstudio_classify):
        results = core.orchestrator.route_parallel(["hola", "adios"])
        assert len(results) == 2
        for r in results:
            assert isinstance(r, dict)
