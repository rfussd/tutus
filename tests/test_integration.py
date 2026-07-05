from __future__ import annotations

"""Integration tests for web server, pipeline, and other core modules."""


class TestWebServer:
    """Test web server API endpoints."""

    def test_health_endpoint(self):
        from fastapi.testclient import TestClient

        from web.server import app

        client = TestClient(app)
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_info_endpoint(self, monkeypatch):
        from fastapi.testclient import TestClient

        from web.server import app

        class MockKG:
            def get_stats(self):
                return {"triples": 0, "entities": []}

            def get_graph_insights(self):
                return {"triples": 0, "entities": [], "recent_memories": []}

        monkeypatch.setattr(
            "core.knowledge_graph.get_knowledge_graph",
            lambda: MockKG(),
        )

        client = TestClient(app)
        resp = client.get("/api/info")
        assert resp.status_code == 200
        data = resp.json()
        assert "model" in data
        assert "kg_triples" in data

    def test_index_returns_html(self):
        from fastapi.testclient import TestClient

        from web.server import app

        client = TestClient(app)
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/html")


class TestPipeline:
    """Test pipeline module."""

    def test_import(self):
        import core.pipeline

        assert hasattr(core.pipeline, "AsyncPipeline")
        assert hasattr(core.pipeline, "ContinuousVoiceEngine")

    def test_async_pipeline_create(self):
        from core.pipeline import AsyncPipeline

        p = AsyncPipeline()
        assert p is not None


class TestPluginLoader:
    def test_import(self):
        import core.plugin_loader

        assert hasattr(core.plugin_loader, "discover_plugins")
        assert hasattr(core.plugin_loader, "load_all_plugins")

    def test_discover_plugins(self):
        from core.plugin_loader import discover_plugins

        plugins = discover_plugins()
        assert isinstance(plugins, list)

    def test_load_all_plugins(self):
        from core.plugin_loader import load_all_plugins

        loaded = load_all_plugins()
        assert isinstance(loaded, list)


class TestUserProfile:
    def test_import(self):
        import core.user_profile

        assert hasattr(core.user_profile, "get_preference")
        assert hasattr(core.user_profile, "get_user_profile_summary")

    def test_get_preference_default(self):
        from core.user_profile import get_preference

        val = get_preference("nonexistent_key", default="default_val")
        assert val == "default_val"

    def test_update_and_get_preference(self):
        from core.user_profile import get_preference, update_preference

        update_preference("test_key", "test_value")
        val = get_preference("test_key")
        assert val == "test_value"


class TestConversation:
    def test_get_buffer(self):
        from core.conversation import get_buffer

        buf = get_buffer()
        assert isinstance(buf, list)

    def test_add_and_clear(self):
        from core.conversation import add_to_buffer, get_buffer

        get_buffer().clear()
        add_to_buffer("user", "test")
        assert len(get_buffer()) >= 1
        get_buffer().clear()
        assert len(get_buffer()) == 0
