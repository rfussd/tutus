from tests.helpers import MockResponse


class TestBaseAgentThink:
    def test_think_returns_decision(self, mock_lmstudio, monkeypatch):
        monkeypatch.setattr("agents.base_agent.STREAMING_ENABLED", False)
        monkeypatch.setattr("core.config.STREAMING_ENABLED", False)
        from agents.base_agent import BaseAgent

        agent = BaseAgent()
        agent.name = "TestAgent"
        agent.system_prompt = "Test system prompt"

        from core.config import LM_STUDIO_URL

        mock_lmstudio[LM_STUDIO_URL] = MockResponse(
            json_data={"choices": [{"message": {"content": '{"action": "none", "params": {}, "message": "ok"}'}}]}
        )

        result = agent.think({"domain": "chat", "intent": "greet"}, "hola")
        assert result["action"] == "none"
        assert result["message"] == "ok"

    def test_think_invalid_json_fallback(self, mock_lmstudio, monkeypatch):
        monkeypatch.setattr("core.config.STREAMING_ENABLED", False)
        from agents.base_agent import BaseAgent

        agent = BaseAgent()
        agent.name = "TestAgent"

        from core.config import LM_STUDIO_URL

        mock_lmstudio[LM_STUDIO_URL] = MockResponse(json_data={"choices": [{"message": {"content": "no json"}}]})

        result = agent.think({"domain": "chat"}, "test")
        assert result["action"] == "none"

    def test_think_empty_choices_doesnt_crash(self, mock_lmstudio, monkeypatch):
        monkeypatch.setattr("core.config.STREAMING_ENABLED", False)
        from agents.base_agent import BaseAgent

        agent = BaseAgent()
        agent.name = "TestAgent"

        from core.config import LM_STUDIO_URL

        mock_lmstudio[LM_STUDIO_URL] = MockResponse(json_data={"choices": []})

        result = agent.think({"domain": "chat"}, "test")
        assert result["action"] == "none"

    def test_think_with_on_token(self, mock_lmstudio, mock_streamer):
        from agents.base_agent import BaseAgent

        agent = BaseAgent()
        agent.name = "TestAgent"

        tokens = []
        result = agent.think(
            {"domain": "chat", "intent": "greet"},
            "hola",
            on_token=lambda t: tokens.append(t),
        )
        assert isinstance(result, dict)


class TestBaseAgentExecute:
    def test_execute_none_action(self):
        from agents.base_agent import BaseAgent

        agent = BaseAgent()
        result = agent.execute({"action": "none", "message": "ok"})
        assert result == "ok"

    def test_execute_unknown_action(self):
        from agents.base_agent import BaseAgent

        agent = BaseAgent()
        result = agent.execute({"action": "nonexistent_skill", "params": {}, "message": "fallback"})
        assert "nonexistent_skill" in result
        assert "no disponible" in result

    def test_execute_skill_success(self):
        from agents.base_agent import BaseAgent

        agent = BaseAgent()
        agent.skills = {"test_skill": lambda **kw: f"executed with {kw}"}
        result = agent.execute({"action": "test_skill", "params": {"x": 1}})
        assert "executed" in result

    def test_execute_skill_error(self):
        from agents.base_agent import BaseAgent

        agent = BaseAgent()
        agent.skills = {"failing": lambda **kw: (_ for _ in ()).throw(ValueError("fail"))}
        result = agent.execute({"action": "failing"})
        assert "Error ejecutando" in result


class TestBaseAgentHandle:
    def test_handle_calls_think_and_execute(self, mock_lmstudio, monkeypatch):
        monkeypatch.setattr("agents.base_agent.STREAMING_ENABLED", False)
        monkeypatch.setattr("core.config.STREAMING_ENABLED", False)
        from agents.base_agent import BaseAgent

        agent = BaseAgent()
        agent.name = "TestAgent"
        agent.system_prompt = "test"

        from core.config import LM_STUDIO_URL

        mock_lmstudio[LM_STUDIO_URL] = MockResponse(
            json_data={"choices": [{"message": {"content": '{"action": "none", "params": {}, "message": "respuesta"}'}}]}
        )

        result = agent.handle({"domain": "chat"}, "hola")
        assert result == "respuesta"
