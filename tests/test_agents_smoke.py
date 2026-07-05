"""Smoke tests para todos los agentes. Solo verifican que instancian y exponen dominio."""

from __future__ import annotations

import pytest


@pytest.fixture
def no_streaming(monkeypatch):
    monkeypatch.setattr("agents.base_agent.STREAMING_ENABLED", False)
    monkeypatch.setattr("core.config.STREAMING_ENABLED", False)


@pytest.fixture
def no_learn(monkeypatch):
    monkeypatch.setattr("agents.base_agent.BaseAgent._learn", lambda *a, **kw: None)


class TestCodeAgent:
    def test_domain_and_name(self, no_streaming):
        from agents.code_agent import CodeAgent

        agent = CodeAgent()
        assert agent.domain == "code"
        assert hasattr(agent, "handle")


class TestDocsAgent:
    def test_domain_and_name(self, no_streaming):
        from agents.docs_agent import DocsAgent

        agent = DocsAgent()
        assert agent.domain == "docs"


class TestFilesAgent:
    def test_domain_and_name(self, no_streaming):
        from agents.files_agent import FilesAgent

        agent = FilesAgent()
        assert agent.domain == "files"


class TestMemoryAgent:
    def test_domain_and_name(self, no_streaming):
        from agents.memory_agent import MemoryAgent

        agent = MemoryAgent()
        assert agent.domain == "memory"


class TestVisionAgent:
    def test_domain_and_name(self, no_streaming):
        from agents.vision_agent import VisionAgent

        agent = VisionAgent()
        assert agent.domain == "vision"


class TestWindowsAgent:
    def test_domain_and_name(self, no_streaming):
        from agents.windows_agent import WindowsAgent

        agent = WindowsAgent()
        assert agent.domain == "windows"


class TestBrowserAgent:
    def test_domain_and_name(self, no_streaming):
        from agents.browser_agent import BrowserAgent

        agent = BrowserAgent()
        assert agent.domain == "browser"


class TestProjectAgent:
    def test_domain_and_name(self, no_streaming):
        from agents.project_agent import ProjectAgent

        agent = ProjectAgent()
        assert agent.domain == "dev"


class TestDocsAgentHandle:
    def test_handle_creates_decision(self, no_streaming, no_learn, monkeypatch):
        from agents.docs_agent import DocsAgent

        monkeypatch.setattr(
            "agents.docs_agent.DocsAgent._word_with_ai",
            lambda self, filename, topic: f"Documento creado: {filename}",
        )

        agent = DocsAgent()

        def mock_llm(system, user, **kw):
            return '{"action":"create_word","params":{"filename":"test","topic":"test"},"message":"ok"}'

        agent._llm_call = mock_llm
        result = agent.handle(
            {"domain": "docs", "intent": "create", "query": "haz un word"},
            "haz un word",
        )
        assert isinstance(result, str)
        assert "test" in result.lower()
