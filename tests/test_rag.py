import tempfile
from pathlib import Path

import pytest


class MockArray:
    def __init__(self, data):
        self._data = data

    def tolist(self):
        return self._data


class MockEmbedder:
    def encode(self, texts, show_progress_bar=False):
        return MockArray([[0.1, 0.2, 0.3] for _ in texts])


class MockCollection:
    def __init__(self):
        self.data = {}

    def count(self):
        return len(self.data)

    def get(self, ids=None, **kwargs):
        return {"ids": []}

    def add(self, ids, embeddings, documents, metadatas):
        for i, id_ in enumerate(ids):
            self.data[id_] = {"doc": documents[i], "meta": metadatas[i]}

    def query(self, query_embeddings, n_results, **kwargs):
        ids = list(self.data.keys())[:n_results]
        return {
            "documents": [[self.data[i]["doc"] for i in ids]],
            "metadatas": [[self.data[i]["meta"] for i in ids]],
            "distances": [[0.1] * len(ids)],
        }


@pytest.fixture
def mock_rag(monkeypatch):
    collection = MockCollection()
    embedder = MockEmbedder()
    monkeypatch.setattr("core.rag._get_embedder", lambda: embedder)
    monkeypatch.setattr("core.rag._get_collection", lambda: collection)

    tmp_dir = tempfile.mkdtemp()
    monkeypatch.setattr("core.rag.DOCUMENTS_DIR", Path(tmp_dir))

    doc_file = Path(tmp_dir) / "test.txt"
    doc_file.write_text("Este es un documento de prueba con informacion util sobre Python.", encoding="utf-8")

    yield collection, embedder, Path(tmp_dir)

    import shutil

    shutil.rmtree(tmp_dir, ignore_errors=True)


class TestIndexDocumentsFolder:
    def test_index_documents_folder(self, mock_rag):
        from core.rag import index_documents_folder

        result = index_documents_folder()
        assert "Indexado" in result
        assert "test.txt" in result

    def test_index_documents_folder_no_dir(self, monkeypatch):
        tmp = tempfile.mkdtemp()
        empty_dir = Path(tmp) / "nonexistent"
        monkeypatch.setattr("core.rag.DOCUMENTS_DIR", empty_dir)
        from core.rag import index_documents_folder

        result = index_documents_folder()
        assert "No hay" in result
        import shutil

        shutil.rmtree(tmp, ignore_errors=True)

    def test_index_documents_folder_no_supported_files(self, monkeypatch):
        tmp = tempfile.mkdtemp()
        monkeypatch.setattr("core.rag.DOCUMENTS_DIR", Path(tmp))
        collection = MockCollection()
        embedder = MockEmbedder()
        monkeypatch.setattr("core.rag._get_embedder", lambda: embedder)
        monkeypatch.setattr("core.rag._get_collection", lambda: collection)
        from core.rag import index_documents_folder

        result = index_documents_folder()
        assert "archivo" in result.lower()
        import shutil

        shutil.rmtree(tmp, ignore_errors=True)


class TestSearchDocuments:
    def test_search_no_docs(self, monkeypatch):
        collection = MockCollection()
        embedder = MockEmbedder()
        monkeypatch.setattr("core.rag._get_embedder", lambda: embedder)
        monkeypatch.setattr("core.rag._get_collection", lambda: collection)
        from core.rag import search_documents

        result = search_documents("python")
        assert "No hay documentos" in result

    def test_search_with_results(self, mock_rag):
        collection, _, _ = mock_rag
        collection.add(
            ids=["hash1"],
            embeddings=[[0.1, 0.2, 0.3]],
            documents=["Python es un lenguaje de programacion"],
            metadatas=[{"source": "test.txt", "chunk_index": 0}],
        )
        from core.rag import search_documents

        result = search_documents("python")
        assert "test.txt" in result
        assert "Python" in result

    def test_search_with_custom_top_k(self, mock_rag):
        collection, _, _ = mock_rag
        for i in range(5):
            collection.add(
                ids=[f"hash{i}"],
                embeddings=[[0.1, 0.2, 0.3]],
                documents=[f"Documento {i}"],
                metadatas=[{"source": "test.txt", "chunk_index": i}],
            )
        from core.rag import search_documents

        result = search_documents("test", top_k=2)
        assert result.count("test.txt") == 2


class TestGetRagContext:
    def test_get_context_no_docs(self, monkeypatch):
        collection = MockCollection()
        embedder = MockEmbedder()
        monkeypatch.setattr("core.rag._get_embedder", lambda: embedder)
        monkeypatch.setattr("core.rag._get_collection", lambda: collection)
        from core.rag import get_rag_context

        result = get_rag_context("python")
        assert result == ""

    def test_get_context_with_results(self, mock_rag):
        collection, _, _ = mock_rag
        collection.add(
            ids=["hash1"],
            embeddings=[[0.1, 0.2, 0.3]],
            documents=["Python es un lenguaje"],
            metadatas=[{"source": "test.txt", "chunk_index": 0}],
        )
        from core.rag import get_rag_context

        result = get_rag_context("python")
        assert "test.txt" in result
        assert "Python" in result
