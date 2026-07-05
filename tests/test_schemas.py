import json

import pytest

from core.schemas import _extract_json, parse_agent_decision, parse_classification


class TestExtractJson:
    def test_simple_object(self):
        assert _extract_json('{"a": 1}') == '{"a": 1}'

    def test_with_prefix_text(self):
        assert _extract_json('texto previo {"a": 1} texto posterior') == '{"a": 1}'

    def test_nested_braces(self):
        raw = '{"a": {"b": [1, 2, {"c": 3}]}}'
        assert _extract_json(raw) == raw

    def test_think_tag_stripped_manually(self):
        raw = '<think>blah</think>{"domain": "chat"}'
        assert _extract_json(raw) == '{"domain": "chat"}'

    def test_no_json_raises(self):
        with pytest.raises(ValueError, match="JSON"):
            _extract_json("solo texto sin llaves")

    def test_multiple_objects(self):
        raw = '{"a": 1} luego {"b": 2}'
        assert _extract_json(raw) == '{"a": 1}'

    def test_empty_braces(self):
        assert _extract_json("{}") == "{}"

    def test_with_newlines(self):
        raw = '{\n  "a": 1\n}'
        assert _extract_json(raw) == '{\n  "a": 1\n}'


class TestParseClassification:
    def test_basic(self):
        raw = json.dumps(
            {
                "domain": "chat",
                "intent": "greet",
                "query": "hola",
                "platform": None,
                "confidence": 0.99,
            }
        )
        result = parse_classification(raw)
        assert result.domain == "chat"
        assert result.intent == "greet"
        assert result.confidence == 0.99

    def test_music_domain(self):
        raw = json.dumps(
            {
                "domain": "music",
                "intent": "play",
                "query": "jose jose",
                "platform": "spotify",
                "confidence": 0.95,
            }
        )
        result = parse_classification(raw)
        assert result.domain == "music"
        assert result.platform == "spotify"

    def test_null_strings_normalized(self):
        raw = '{"domain": "chat", "intent": "greet", "query": "null", "platform": "null", "confidence": 0.9}'
        result = parse_classification(raw)
        assert result.query is None
        assert result.platform is None

    def test_invalid_domain_raises(self):
        raw = '{"domain": "invalid_domain_12345", "intent": "test", "confidence": 0.5}'
        with pytest.raises(ValueError):
            parse_classification(raw)

    def test_think_wrapped(self):
        raw = '<think>analizando</think>{"domain":"chat","intent":"greet","confidence":0.99}'
        result = parse_classification(raw)
        assert result.domain == "chat"

    def test_text_after_json(self):
        raw = '{"domain":"chat","intent":"greet","confidence":0.99} y eso es todo'
        result = parse_classification(raw)
        assert result.domain == "chat"


class TestParseAgentDecision:
    def test_basic(self):
        raw = json.dumps(
            {
                "action": "none",
                "params": {},
                "message": "Hola",
            }
        )
        result = parse_agent_decision(raw)
        assert result.action == "none"
        assert result.message == "Hola"

    def test_with_params(self):
        raw = json.dumps(
            {
                "action": "spotify_play",
                "params": {"query": "jose jose"},
                "message": "reproduciendo",
            }
        )
        result = parse_agent_decision(raw)
        assert result.action == "spotify_play"
        assert result.params["query"] == "jose jose"

    def test_null_action_normalized(self):
        raw = '{"action": "none", "params": {}, "message": "ok"}'
        result = parse_agent_decision(raw)
        assert result.action == "none"

    def test_newlines_in_message(self):
        raw = '{"action": "none", "params": {}, "message": "line1\\nline2"}'
        result = parse_agent_decision(raw)
        assert "line1" in result.message
