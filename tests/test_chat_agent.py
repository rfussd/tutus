from tests.helpers import MockResponse


class TestChatAgentHandle:
    def test_handle_non_streaming(self, mock_lmstudio):
        from agents.chat_agent import ChatAgent

        agent = ChatAgent()

        from core.config import LM_STUDIO_URL

        mock_lmstudio[LM_STUDIO_URL] = MockResponse(json_data={"choices": [{"message": {"content": "¡Hola! ¿En qué te ayudo?"}}]})

        result = agent.handle(
            {"domain": "chat", "intent": "greet", "query": "hola", "confidence": 0.99},
            "hola",
        )
        assert "Hola" in result or "ayudo" in result

    def test_handle_with_streaming(self, mock_lmstudio, mock_streamer):
        from agents.chat_agent import ChatAgent

        agent = ChatAgent()

        tokens = []
        result = agent.handle(
            {"domain": "chat", "intent": "greet"},
            "hola",
            on_token=lambda t: tokens.append(t),
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_handle_connection_error(self, mock_lmstudio):
        from agents.chat_agent import ChatAgent

        agent = ChatAgent()

        import requests

        from core.config import LM_STUDIO_URL

        def failing(url, **kwargs):
            raise requests.ConnectionError("fail")

        mock_lmstudio[LM_STUDIO_URL] = failing

        result = agent.handle({"domain": "chat"}, "hola")
        assert "conectarme" in result.lower() or "LM Studio" in result

    def test_handle_think_tag_stripped(self, mock_lmstudio):
        from agents.chat_agent import ChatAgent

        agent = ChatAgent()

        from core.config import LM_STUDIO_URL

        mock_lmstudio[LM_STUDIO_URL] = MockResponse(
            json_data={"choices": [{"message": {"content": "<think>analizando</think>Hola que tal"}}]}
        )

        result = agent.handle({"domain": "chat"}, "hola")
        assert "<think>" not in result
        assert "Hola que tal" in result


class TestDetectLanguage:
    def test_detect_spanish(self):
        from agents.chat_agent import _detect_language

        lang = _detect_language("hola que tal")
        assert lang in ("es", "ca")

    def test_detect_english(self):
        from agents.chat_agent import _detect_language

        lang = _detect_language("hello how are you")
        assert lang == "en"

    def test_detect_no_langdetect_fallback(self, monkeypatch):
        import builtins
        import sys

        sys.modules.pop("langdetect", None)
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "langdetect":
                raise ImportError("mocked")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)
        from agents.chat_agent import _detect_language

        lang = _detect_language("hola")
        assert lang == "es"
