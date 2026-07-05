import os
import tempfile

import pytest

from tests.helpers import MockResponse


@pytest.fixture
def kg():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    from core.knowledge_graph import KnowledgeGraph

    graph = KnowledgeGraph(db_path=tmp.name)
    yield graph
    try:
        os.unlink(tmp.name)
    except Exception:
        pass


@pytest.fixture
def reset_kg_singleton(monkeypatch):
    monkeypatch.setattr("core.knowledge_graph._knowledge_graph", None)


class TestKnowledgeGraph:
    def test_add_and_get_entity_info(self, kg):
        kg.add_triple("david", "gusta", "python", context="test", source="manual")
        info = kg.get_entity_info("david")
        assert len(info) >= 1
        assert info[0]["relation"] == "gusta"
        assert info[0]["target"] == "python"
        assert info[0]["direction"] == "out"

    def test_get_entity_info_inbound(self, kg):
        kg.add_triple("david", "jefe_de", "juan", context="test", source="manual")
        info = kg.get_entity_info("juan")
        inbound = [i for i in info if i["direction"] == "in"]
        assert len(inbound) >= 1
        assert inbound[0]["source"] == "david"

    def test_get_entity_info_empty(self, kg):
        info = kg.get_entity_info("nonexistent")
        assert info == []

    def test_query_relation(self, kg):
        kg.add_triple("david", "gusta", "python", context="test", source="manual")
        kg.add_triple("david", "gusta", "javascript", context="test", source="manual")
        results = kg.query_relation("david", "gusta")
        assert len(results) == 2
        assert "python" in results
        assert "javascript" in results

    def test_query_relation_empty(self, kg):
        results = kg.query_relation("david", "nonexistent")
        assert results == []

    def test_query_entities_by_relation(self, kg):
        kg.add_triple("david", "gusta", "python", context="test", source="manual")
        kg.add_triple("juan", "gusta", "python", context="test", source="manual")
        results = kg.query_entities_by_relation("gusta", "python")
        assert len(results) == 2
        assert "david" in results
        assert "juan" in results

    def test_search_entities(self, kg):
        kg.add_triple("david", "gusta", "python", context="test", source="manual")
        kg.add_triple("david", "trabaja_en", "empresa", context="test", source="manual")
        results = kg.search_entities("dav")
        assert "david" in results

    def test_search_entities_no_match(self, kg):
        results = kg.search_entities("zzzzz")
        assert results == []

    def test_get_all_entities(self, kg):
        kg.add_triple("david", "gusta", "python", context="test", source="manual")
        kg.add_triple("juan", "usa", "docker", context="test", source="manual")
        entities = kg.get_all_entities()
        assert "david" in entities
        assert "python" in entities
        assert "juan" in entities
        assert "docker" in entities

    def test_get_stats(self, kg):
        kg.add_triple("david", "gusta", "python", context="test", source="manual")
        stats = kg.get_stats()
        assert stats["triples"] >= 1
        assert stats["entities"] >= 2

    def test_fmt_entity_info_known(self, kg):
        kg.add_triple("david", "gusta", "python", context="test", source="manual")
        formatted = kg.fmt_entity_info("david")
        assert "David" in formatted
        assert "gusta" in formatted
        assert "python" in formatted

    def test_fmt_entity_info_unknown(self, kg):
        formatted = kg.fmt_entity_info("unknown_entity_xyz")
        assert "No tengo" in formatted

    def test_add_triples_from_text_pattern(self, kg):
        triples = kg.add_triples_from_text("david usa python.", use_llm=False)
        assert len(triples) >= 1
        assert triples[0][1] == "usa"

    def test_add_triples_from_text_no_match(self, kg):
        triples = kg.add_triples_from_text("esto no contiene patrones.", use_llm=False)
        assert triples == []

    def test_add_triples_from_text_llm_fallback(self, kg, monkeypatch):
        def mock_post(url, **kwargs):
            return MockResponse(json_data={"choices": [{"message": {"content": '[["david", "gusta", "python"]]'}}]})

        monkeypatch.setattr("requests.post", mock_post)
        triples = kg.add_triples_from_text("some random unstructured text.", use_llm=True)
        assert len(triples) == 1
        assert triples[0] == ["david", "gusta", "python"]

    def test_add_triples_from_text_llm_returns_empty(self, kg, monkeypatch):
        def mock_post(url, **kwargs):
            return MockResponse(json_data={"choices": [{"message": {"content": "[]"}}]})

        monkeypatch.setattr("requests.post", mock_post)
        triples = kg.add_triples_from_text("some random text.", use_llm=True)
        assert triples == []

    def test_get_graph_insights(self, kg):
        kg.add_triple("david", "gusta", "python", context="test", source="manual")
        kg.add_triple("david", "gusta", "javascript", context="test", source="manual")
        insights = kg.get_graph_insights()
        assert "Knowledge Graph" in insights
        assert "david" in insights.lower()


class TestGetKnowledgeGraph:
    def test_get_knowledge_graph_singleton(self, reset_kg_singleton):
        from core.knowledge_graph import KnowledgeGraph, get_knowledge_graph

        kg1 = get_knowledge_graph()
        kg2 = get_knowledge_graph()
        assert kg1 is kg2
        assert isinstance(kg1, KnowledgeGraph)
