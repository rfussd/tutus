import core.agent_router
from tests.helpers import MockResponse


class TestRoute:
    def test_route_chat(self, mock_lmstudio_classify):
        result = core.agent_router.route("hola")
        assert result["domain"] == "chat"

    def test_route_music(self, mock_lmstudio_classify, mock_lmstudio, monkeypatch):
        from core.config import LM_STUDIO_URL

        monkeypatch.setattr("agents.base_agent.STREAMING_ENABLED", False)
        monkeypatch.setattr("core.config.STREAMING_ENABLED", False)

        mock_lmstudio[LM_STUDIO_URL] = [
            MockResponse(
                json_data={
                    "choices": [
                        {
                            "message": {
                                "content": '{"domain":"music","intent":"play","query":"jose jose","platform":"spotify","confidence":0.95}'
                            }
                        }
                    ]
                }
            ),
            MockResponse(
                json_data={
                    "choices": [
                        {"message": {"content": '{"action":"spotify_play","params":{"query":"jose jose"},"message":"reproduciendo"}'}}
                    ]
                }
            ),
        ]

        result = core.agent_router.route("pon jose jose")
        assert result["domain"] == "music"

    def test_route_unhandled_domain(self, mock_lmstudio_classify):
        mock_lmstudio_classify('{"domain":"nonexistent","intent":"test","confidence":0.5}')

        result = core.agent_router.route("test")
        msg = result.get("message", "")
        assert "manejar" in msg or "no sé" in msg.lower()

    def test_route_confirm_computer(self, mock_lmstudio_classify):
        mock_lmstudio_classify('{"domain":"computer","intent":"move_mouse","query":"mueve el mouse","confidence":0.97}')

        result = core.agent_router.route("mueve el mouse")
        assert result.get("action") == "confirm"
        assert "Confirmo" in result.get("message", "")

    def test_route_cancel_pending(self):
        core.agent_router._pending_action = {
            "domain": "computer",
            "classification": {"domain": "computer"},
            "message": "mueve el mouse",
        }

        result = core.agent_router.route("no")
        assert result.get("action") == "cancelled"
        assert core.agent_router._pending_action is None

    def test_route_confirm_pending(self, mock_lmstudio, monkeypatch):
        monkeypatch.setattr("core.config.STREAMING_ENABLED", False)
        from core.config import LM_STUDIO_URL

        core.agent_router._pending_action = {
            "domain": "computer",
            "classification": {"domain": "computer", "intent": "move_mouse"},
            "message": "mueve el mouse",
        }

        mock_lmstudio[LM_STUDIO_URL] = MockResponse(
            json_data={"choices": [{"message": {"content": '{"action":"none","params":{},"message":"movido"}'}}]}
        )

        core.agent_router.route("sí")
        assert core.agent_router._pending_action is None


class TestGetAgent:
    def test_get_chat_agent(self):
        agent = core.agent_router.get_agent("chat")
        assert agent is not None
        assert agent.name == "ChatAgent"

    def test_get_music_agent(self):
        agent = core.agent_router.get_agent("music")
        assert agent is not None
        assert agent.domain == "music"

    def test_get_nonexistent_agent(self):
        assert core.agent_router.get_agent("nonexistent_12345") is None
