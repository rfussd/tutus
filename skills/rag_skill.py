from __future__ import annotations

from core.rag import index_document, index_documents_folder, search_documents


def indexar_archivo(filepath: str) -> str:
    return index_document(filepath)


def indexar_documentos() -> str:
    return index_documents_folder()


def buscar_en_documentos(query: str) -> str:
    return search_documents(query)
