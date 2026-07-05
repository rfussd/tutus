"""End-to-end (integration) tests for TUTUS.
Tests full agent-skill chains: classification routing agent handle skill execution response.
All external services (LM Studio, Spotify, subprocess, browser) are mocked."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from tests.helpers import MockResponse

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _no_streaming(monkeypatch):
    monkeypatch.setattr("agents.base_agent.STREAMING_ENABLED", False)
    monkeypatch.setattr("core.config.STREAMING_ENABLED", False)


def _mock_learn(monkeypatch):
    monkeypatch.setattr("agents.base_agent.BaseAgent._learn", lambda *a, **kw: None)


def _clear_agent_cache(domains: list[str] | None = None):
    """Remove cached agents so they are re-created with patched skills."""
    import core.agent_router as ar

    if domains is None:
        ar._agents.clear()
    else:
        for d in domains:
            ar._agents.pop(d, None)


def _mock_classify(monkeypatch, response: dict):
    """Mock classify at the agent_router level (where route() imports it)."""
    monkeypatch.setattr(
        "core.agent_router.classify",
        lambda msg, **kw: response,
    )


def _make_post_spy(monkeypatch, responses: list):
    """Replace requests.post with a spy that returns canned responses."""
    idx = [0]

    def spy(url, **kwargs):
        if idx[0] < len(responses):
            r = responses[idx[0]]
            idx[0] += 1
            return r
        return MockResponse(json_data={"choices": [{"message": {"content": '{"domain":"chat","intent":"unknown","confidence":0}'}}]})

    monkeypatch.setattr("requests.post", spy)
    return spy


@pytest.fixture
def reset_context():
    import core.context
    import core.conversation

    core.context._conversation_summary = ""
    core.conversation._conversation_buffer.clear()


@pytest.fixture
def reset_kg():
    import core.knowledge_graph as kg_mod

    tmp = tempfile.NamedTemporaryFile(suffix=".kg_e2e.db", delete=False)
    tmp.close()
    kg = kg_mod.KnowledgeGraph(db_path=tmp.name)
    old = kg_mod._knowledge_graph
    kg_mod._knowledge_graph = kg
    yield kg
    kg_mod._knowledge_graph = old
    try:
        os.unlink(tmp.name)
    except Exception:
        pass


# ===========================================================================
# 1. TestMusicAgentE2E — full music chain
# ===========================================================================


class TestMusicAgentE2E:
    """Verify the complete music flow: classify think execute skill."""

    def test_music_play_song(self, mock_lmstudio, monkeypatch, temp_db):
        _no_streaming(monkeypatch)
        _mock_learn(monkeypatch)
        from core.config import LM_STUDIO_URL

        mock_lmstudio[LM_STUDIO_URL] = [
            MockResponse(
                json_data={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "domain": "music",
                                        "intent": "play",
                                        "query": "jose jose",
                                        "platform": "spotify",
                                        "confidence": 0.95,
                                    }
                                )
                            }
                        }
                    ]
                }
            ),
            MockResponse(
                json_data={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "action": "spotify_play",
                                        "params": {"query": "jose jose"},
                                        "message": "Voy a poner Jose Jose",
                                    }
                                )
                            }
                        }
                    ]
                }
            ),
        ]

        monkeypatch.setattr(
            "skills.spotify_skill.spotify_play",
            lambda query="", **kw: f"Reproduciendo: {query} -- Jose Jose",
        )

        # Clear cached agent so a fresh one picks up the patched skill
        _clear_agent_cache(["music"])

        import core.agent_router

        result = core.agent_router.route("pon jose jose")

        assert result["domain"] == "music"
        assert "reproduciendo" in result["message"].lower()
        assert "jose jose" in result["message"].lower()

    def test_music_artist_query(self, mock_lmstudio, monkeypatch, temp_db):
        _no_streaming(monkeypatch)
        _mock_learn(monkeypatch)
        from core.config import LM_STUDIO_URL

        mock_lmstudio[LM_STUDIO_URL] = MockResponse(
            json_data={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "domain": "music",
                                    "intent": "play",
                                    "query": "bad bunny",
                                    "platform": "spotify",
                                    "confidence": 0.95,
                                }
                            )
                        }
                    }
                ]
            }
        )

        import core.agent_router

        result = core.agent_router.route("musica de bad bunny")

        assert result["domain"] == "music"
        assert result["classification"]["query"] == "bad bunny"


# ===========================================================================
# 2. TestSystemAgentE2E — system / launch / browser
# ===========================================================================


class TestSystemAgentE2E:
    """Verify system commands: launch app and open browser."""

    def test_system_launch_app(self, mock_lmstudio, monkeypatch, temp_db):
        _no_streaming(monkeypatch)
        _mock_learn(monkeypatch)
        from core.config import LM_STUDIO_URL

        mock_lmstudio[LM_STUDIO_URL] = [
            MockResponse(
                json_data={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "domain": "system",
                                        "intent": "launch",
                                        "query": "Spotify",
                                        "confidence": 0.95,
                                    }
                                )
                            }
                        }
                    ]
                }
            ),
            MockResponse(
                json_data={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "action": "open_app",
                                        "params": {"app": "spotify"},
                                        "message": "Abriendo Spotify",
                                    }
                                )
                            }
                        }
                    ]
                }
            ),
        ]

        monkeypatch.setattr(
            "skills.system_skill.open_app",
            lambda app="", **kw: f"Abriendo {app}",
        )

        _clear_agent_cache(["system"])

        import core.agent_router

        result = core.agent_router.route("abre Spotify")

        assert result["domain"] == "system"
        assert "abriendo" in result["message"].lower()
        assert "spotify" in result["message"].lower()

    def test_system_open_browser(self, mock_lmstudio, monkeypatch, temp_db):
        _no_streaming(monkeypatch)
        _mock_learn(monkeypatch)
        from core.config import LM_STUDIO_URL

        mock_lmstudio[LM_STUDIO_URL] = [
            MockResponse(
                json_data={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "domain": "system",
                                        "intent": "open_browser",
                                        "query": "https://youtube.com",
                                        "confidence": 0.95,
                                    }
                                )
                            }
                        }
                    ]
                }
            ),
            MockResponse(
                json_data={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "action": "open_browser",
                                        "params": {"url": "https://youtube.com"},
                                        "message": "Abriendo youtube",
                                    }
                                )
                            }
                        }
                    ]
                }
            ),
        ]

        monkeypatch.setattr(
            "skills.browser_skill.navigate",
            lambda url="", **kw: f"Navegando a: {url}",
        )

        _clear_agent_cache(["system"])

        import core.agent_router

        result = core.agent_router.route("abre youtube")

        assert result["domain"] == "system"
        assert "youtube" in result["message"].lower() or "navegando" in result["message"].lower()


# ===========================================================================
# 3. TestKnowledgeAgentE2E — knowledge graph queries and learning
# ===========================================================================


class TestKnowledgeAgentE2E:
    """Verify knowledge flow: graph insights and learning."""

    def test_knowledge_query(self, reset_kg, temp_db, monkeypatch):
        _no_streaming(monkeypatch)
        _mock_learn(monkeypatch)

        kg = reset_kg
        kg.add_triple("david", "gusta", "python", context="test", source="manual")
        kg.add_triple("david", "trabaja_en", "tech", context="test", source="manual")

        _mock_classify(
            monkeypatch,
            {
                "domain": "knowledge",
                "intent": "query",
                "query": "david",
                "confidence": 0.95,
            },
        )

        import core.agent_router

        result = core.agent_router.route("que sabes de david")

        assert result["domain"] == "knowledge"
        msg = result["message"].lower()
        assert "python" in msg or "david" in msg or "gusta" in msg or "tech" in msg

    def test_knowledge_learn(self, reset_kg, temp_db, monkeypatch):
        _no_streaming(monkeypatch)

        _mock_classify(
            monkeypatch,
            {
                "domain": "knowledge",
                "intent": "learn",
                "query": "me gusta el cafe",
                "confidence": 0.95,
            },
        )

        # If BaseAgent._learn() fires, it may try LLM extraction via requests.
        # Provide a fallback response so it doesn't crash.
        _make_post_spy(
            monkeypatch,
            [
                MockResponse(json_data={"choices": [{"message": {"content": "[]"}}]}),
            ],
        )

        import core.agent_router

        result = core.agent_router.route("aprende que me gusta el cafe")

        msg = result["message"].lower()
        assert "aprend" in msg or "cosas" in msg or "gusta" in msg or "cafe" in msg


# ===========================================================================
# 4. TestReminderAgentE2E — reminder creation
# ===========================================================================


class TestReminderAgentE2E:
    """Verify reminder creation flow."""

    def test_reminder_create(self, monkeypatch, temp_db):
        _no_streaming(monkeypatch)
        _mock_learn(monkeypatch)

        _mock_classify(
            monkeypatch,
            {
                "domain": "reminder",
                "intent": "add",
                "query": "algo",
                "confidence": 0.95,
            },
        )

        # ReminderAgent.think() does `from core.streamer import stream_chat`
        # at call time (inside the method), so patching core.streamer.stream_chat
        # is picked up automatically.
        monkeypatch.setattr(
            "core.streamer.stream_chat",
            lambda **kw: json.dumps(
                {
                    "action": "add_reminder",
                    "params": {"text": "algo", "when": "15:00"},
                    "message": "Recordatorio guardado.",
                }
            ),
        )

        monkeypatch.setattr(
            "core.reminder.add_reminder",
            lambda text="", when="", recurring=None, **kw: f"Recordatorio guardado: '{text}' a las {when}",
        )

        _clear_agent_cache(["reminder"])

        import core.agent_router

        result = core.agent_router.route("recuerdame algo a las 3pm")

        assert result["domain"] == "reminder"
        assert "recordatorio" in result["message"].lower()


# ===========================================================================
# 5. TestMultiIntentE2E — parallel routing
# ===========================================================================


class TestMultiIntentE2E:
    """Verify multi-intent splitting and parallel execution."""

    def test_multi_intent_split(self):
        import core.orchestrator

        parts = core.orchestrator.detect_multi_intent("abre spotify y pon musica")
        assert len(parts) >= 2

    def test_engine_process_multi(self, monkeypatch, temp_db):
        import core.orchestrator

        def mock_classify(msg):
            return {
                "domain": "chat",
                "intent": "greet",
                "query": msg,
                "confidence": 0.99,
            }

        monkeypatch.setattr("core.orchestrator.classify", mock_classify)
        monkeypatch.setattr(
            "agents.chat_agent.ChatAgent.handle",
            lambda self, c, msg, **kw: f"echo: {msg}",
        )

        results = core.orchestrator.route_parallel(["hola", "que tal"])
        assert len(results) == 2
        for r in results:
            assert isinstance(r, dict)
            assert "message" in r


# ===========================================================================
# 6. TestAgentRouterFallbackE2E — fallback chains
# ===========================================================================


class TestAgentRouterFallbackE2E:
    """Verify automatic fallback when agents fail or lack data."""

    def test_knowledge_fallback_to_research_factual(self, reset_kg, temp_db, monkeypatch):
        """Factual query ('qué es X') debe caer a research si knowledge no sabe."""
        _no_streaming(monkeypatch)
        _mock_learn(monkeypatch)
        _clear_agent_cache(["research", "knowledge"])

        class MockResearchAgent:
            domain = "research"

            def handle(self, classification, msg, **kw):
                return f"Investigacion sobre: {classification.get('query', msg)}"

        import core.agent_router

        core.agent_router._agents["research"] = MockResearchAgent()

        kg = reset_kg
        assert kg.get_stats()["triples"] == 0

        _mock_classify(
            monkeypatch,
            {
                "domain": "knowledge",
                "intent": "query",
                "query": "machine learning",
                "confidence": 0.95,
            },
        )

        result = core.agent_router.route("qué es machine learning")
        msg = result["message"].lower()
        assert "investigacion" in msg or "investigación" in msg

    def test_knowledge_no_fallback_for_personal_query(self, reset_kg, temp_db, monkeypatch):
        """Personal query ('qué sabes de...') NO debe caer a research."""
        _no_streaming(monkeypatch)
        _mock_learn(monkeypatch)

        class MockResearchAgent:
            domain = "research"

            def handle(self, classification, msg, **kw):
                return f"Investigacion sobre: {classification.get('query', msg)}"

        import core.agent_router

        core.agent_router._agents["research"] = MockResearchAgent()

        kg = reset_kg
        assert kg.get_stats()["triples"] == 0

        _mock_classify(
            monkeypatch,
            {
                "domain": "knowledge",
                "intent": "query",
                "query": "algo",
                "confidence": 0.95,
            },
        )

        result = core.agent_router.route("que sabes de algo")
        msg = result["message"].lower()
        assert "investigacion" not in msg and "investigación" not in msg

    def test_agent_error_fallback_to_chat(self, monkeypatch, temp_db):
        _no_streaming(monkeypatch)
        _mock_learn(monkeypatch)

        class CrashAgent:
            domain = "crash_test"
            name = "CrashAgent"

            def handle(self, classification, msg, **kw):
                raise RuntimeError("simulated crash")

        import core.agent_router

        core.agent_router._agents["crash_test"] = CrashAgent()

        _mock_classify(
            monkeypatch,
            {
                "domain": "crash_test",
                "intent": "boom",
                "query": "haz algo",
                "confidence": 0.99,
            },
        )

        # ChatAgent.handle() will call requests.post(LM_STUDIO_URL)
        _make_post_spy(
            monkeypatch,
            [
                MockResponse(json_data={"choices": [{"message": {"content": "Esto es un fallback del chat."}}]}),
            ],
        )

        result = core.agent_router.route("haz algo que falle")
        assert result["domain"] == "chat"
        assert result["action"] == "fallback"
        assert len(result["message"]) > 0


# ===========================================================================
# 7. TestPreClassificationE2E — pre-check patterns
# ===========================================================================


class TestPreClassificationE2E:
    """Verify pre-classification regex intercepts common patterns before LLM."""

    def test_pre_classify_greet(self, monkeypatch, temp_db):
        """Saludos básicos van a chat sin pasar por classify()."""
        import core.agent_router

        _no_streaming(monkeypatch)
        _mock_learn(monkeypatch)
        _make_post_spy(
            monkeypatch,
            [
                MockResponse(json_data={"choices": [{"message": {"content": "¡Hola! ¿En qué te ayudo?"}}]}),
            ],
        )
        result = core.agent_router.route("hola")
        assert result["domain"] == "chat"

    def test_pre_classify_greet_variants(self, monkeypatch, temp_db):
        import core.agent_router

        _no_streaming(monkeypatch)
        _mock_learn(monkeypatch)
        _make_post_spy(
            monkeypatch,
            [
                MockResponse(json_data={"choices": [{"message": {"content": "¡Buenas!"}}]}),
            ],
        )
        for msg in ["buenos días", "buenas tardes", "qué tal", "cómo estás", "buenas noches", "que haces", "saludos"]:
            result = core.agent_router.route(msg)
            assert result["domain"] == "chat", f"Fallo para: {msg}"

    def test_pre_classify_identity(self, monkeypatch, temp_db):
        import core.agent_router

        _no_streaming(monkeypatch)
        _mock_learn(monkeypatch)
        _make_post_spy(
            monkeypatch,
            [
                MockResponse(json_data={"choices": [{"message": {"content": "Soy TUTUS, el gato asistente."}}]}),
            ],
        )
        for msg in ["quién eres", "quien eres", "cómo te llamas", "como te llamas", "qué eres", "que eres", "tú quién eres", "quién soy"]:
            result = core.agent_router.route(msg)
            assert result["domain"] == "chat", f"Fallo para: {msg}"

    def test_pre_classify_opinion(self, monkeypatch, temp_db):
        import core.agent_router

        _no_streaming(monkeypatch)
        _mock_learn(monkeypatch)
        _make_post_spy(
            monkeypatch,
            [
                MockResponse(json_data={"choices": [{"message": {"content": "Opino que..."}}]}),
            ],
        )
        for msg in [
            "qué opinas de la IA",
            "qué piensas de eso",
            "quién crees que va a ganar",
            "te gusta la música",
            "crees que va a llover",
            "qué te parece esto",
        ]:
            result = core.agent_router.route(msg)
            assert result["domain"] == "chat", f"Fallo para: {msg}"

    def test_pre_classify_gratitude_and_farewell(self, monkeypatch, temp_db):
        import core.agent_router

        _no_streaming(monkeypatch)
        _mock_learn(monkeypatch)
        _make_post_spy(
            monkeypatch,
            [
                MockResponse(json_data={"choices": [{"message": {"content": "De nada."}}]}),
            ],
        )
        for msg in ["gracias", "muchas gracias", "te agradezco", "adiós", "hasta luego", "nos vemos", "bye"]:
            result = core.agent_router.route(msg)
            assert result["domain"] == "chat", f"Fallo para: {msg}"

    def test_pre_classify_follow_up(self, monkeypatch, temp_db):
        import core.agent_router

        _no_streaming(monkeypatch)
        _mock_learn(monkeypatch)
        _make_post_spy(
            monkeypatch,
            [
                MockResponse(json_data={"choices": [{"message": {"content": "Claro, te explico..."}}]}),
            ],
        )
        for msg in ["por qué", "porque", "cuéntame más", "dime más", "explícame", "ahora qué"]:
            result = core.agent_router.route(msg)
            assert result["domain"] == "chat", f"Fallo para: {msg}"


# ===========================================================================
# 8. TestResearchGuardE2E — research agent identity guard
# ===========================================================================


class TestResearchGuardE2E:
    """Verify ResearchAgent redirects identity questions back instead of web search."""

    def test_research_identity_guard(self, monkeypatch, temp_db):
        """ResearchAgent.think() debe retornar no-action para preguntas de identidad."""
        _no_streaming(monkeypatch)
        _mock_learn(monkeypatch)
        _clear_agent_cache(["research"])

        import core.agent_router

        research = core.agent_router.get_agent("research")

        # Test various identity queries directly on think()
        for msg in ["quién eres", "quien eres", "como te llamas", "qué eres"]:
            decision = research.think(
                {"domain": "research", "intent": "web_search", "query": msg, "confidence": 0.0},
                msg,
            )
            assert decision.get("action") in ("none", ""), f"Identity query '{msg}' no debió producir acción"

    def test_research_identity_not_interfering_with_normal_queries(self, monkeypatch, temp_db):
        """ResearchAgent.think() debe procesar consultas normales sin interferir."""
        _no_streaming(monkeypatch)
        _mock_learn(monkeypatch)
        _clear_agent_cache(["research"])

        import core.agent_router

        research = core.agent_router.get_agent("research")

        # Patch the LLM call to return a web_search decision
        def mock_llm(system, user, **kw):
            return '{"action":"web_search","params":{"query":"inteligencia artificial"},"message":"Buscando..."}'

        research._llm_call = mock_llm

        # A normal research query should NOT be blocked
        decision = research.think(
            {"domain": "research", "intent": "web_search", "query": "inteligencia artificial", "confidence": 0.95},
            "investiga sobre inteligencia artificial",
        )
        assert decision.get("action") == "web_search", "Consulta normal de investigación debe proceder"


# ===========================================================================
# 9. TestConversationContextE2E — conversation buffer
# ===========================================================================


class TestConversationContextE2E:
    """Verify conversation buffer is used in classify and summarization."""

    @pytest.fixture(autouse=True)
    def _clean(self):
        import core.conversation

        core.conversation._conversation_buffer.clear()
        import core.context

        core.context._conversation_summary = ""

    def test_conversation_buffer_used_in_classify(self, monkeypatch):
        import core.orchestrator
        from core.conversation import add_to_buffer, get_buffer

        get_buffer().clear()

        add_to_buffer("user", "me encanta la musica")
        add_to_buffer("assistant", "que buen gusto")

        captured = {"context": ""}

        def tracking_post(url, **kwargs):
            body = kwargs.get("json", {})
            msgs = body.get("messages", [])
            for m in msgs:
                if m["role"] == "system" and "Contexto reciente" in m.get("content", ""):
                    captured["context"] = m["content"]
            return MockResponse(
                json_data={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "domain": "chat",
                                        "intent": "greet",
                                        "query": "hola",
                                        "confidence": 0.99,
                                    }
                                )
                            }
                        }
                    ]
                }
            )

        monkeypatch.setattr("requests.post", tracking_post)
        core.orchestrator.classify("hola")

        assert "me encanta la musica" in captured["context"]
        assert "que buen gusto" in captured["context"]

    def test_summarization_triggered(self, monkeypatch):
        from core.context import auto_summarize_if_needed, get_summary
        from core.conversation import add_to_buffer, get_buffer

        monkeypatch.setattr("core.context.CONTEXT_SUMMARY_THRESHOLD", 2)
        get_buffer().clear()

        summary_text = "El usuario pregunto por la musica."

        def mock_summarize(*a, **kw):
            return MockResponse(json_data={"choices": [{"message": {"content": summary_text}}]})

        monkeypatch.setattr("requests.post", mock_summarize)

        # Fill buffer past threshold (threshold*2 = 4)
        for i in range(5):
            add_to_buffer("user", f"mensaje {i}")
            add_to_buffer("assistant", f"respuesta {i}")

        auto_summarize_if_needed()

        final_summary = get_summary()
        assert len(final_summary) > 0
        assert len(get_buffer()) <= 5


# ===========================================================================
# 8. TestWorkingMemoryE2E — memory interaction
# ===========================================================================


class TestWorkingMemoryE2E:
    """Verify agents use memory_signals context in think() and auto-learn."""

    def test_agent_uses_memory_in_think(self, mock_lmstudio, monkeypatch, temp_db):
        _no_streaming(monkeypatch)
        from core.config import LM_STUDIO_URL
        from core.memory_signals import save_memory, set_signal

        set_signal("music", "preferred_platform", "spotify")
        save_memory("A David le encanta Jose Jose", domain="music")

        lm_calls = []

        def tracking_post(url, **kwargs):
            body = kwargs.get("json", {})
            msgs = body.get("messages", [])
            lm_calls.append(msgs)
            return MockResponse(
                json_data={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "action": "none",
                                        "params": {},
                                        "message": "ok",
                                    }
                                )
                            }
                        }
                    ]
                }
            )

        mock_lmstudio[LM_STUDIO_URL] = tracking_post

        from agents.music_agent import MusicAgent

        agent = MusicAgent()
        agent.think({"domain": "music", "intent": "play", "query": "jose jose"}, "pon jose jose")

        all_text = " ".join(m.get("content", "") for call in lm_calls for m in call)
        assert "spotify" in all_text or "preferred_platform" in all_text

    def test_auto_learn_called(self, mock_lmstudio, temp_db, monkeypatch):
        """Verify that BaseAgent.handle() calls _learn() after execute()."""
        _no_streaming(monkeypatch)

        from agents.music_agent import MusicAgent
        from core.config import LM_STUDIO_URL

        learn_data = {"called": False, "original_message": ""}
        orig_learn = MusicAgent._learn

        def tracking_learn(self, classification, decision, original_message=""):
            learn_data["called"] = True
            learn_data["original_message"] = original_message
            return orig_learn(self, classification, decision, original_message)

        monkeypatch.setattr(MusicAgent, "_learn", tracking_learn)

        mock_lmstudio[LM_STUDIO_URL] = MockResponse(
            json_data={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "action": "spotify_play",
                                    "params": {"query": "jose jose"},
                                    "message": "Reproduciendo",
                                }
                            )
                        }
                    }
                ]
            }
        )

        monkeypatch.setattr(
            "skills.spotify_skill.spotify_play",
            lambda query="", **kw: f"Reproduciendo: {query}",
        )

        agent = MusicAgent()
        agent.handle(
            {"domain": "music", "intent": "play", "query": "jose jose", "confidence": 0.95},
            "me gusta jose jose",
        )

        assert learn_data["called"], "_learn() was never called"
        assert learn_data["original_message"] == "me gusta jose jose"
