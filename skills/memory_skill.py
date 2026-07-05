from __future__ import annotations

from core.memory_signals import forget_memories as _forget
from core.memory_signals import save_memory as _save
from core.memory_signals import search_memories as _search


def save_memory(content: str, domain: str = "general", category: str = "general") -> str:
    if not content.strip():
        return "No hay nada que recordar."

    # Reformatear primera persona → tercera persona
    content = content.strip()

    if len(content.split()) <= 3 and domain == "music":
        content = f"A David le gusta {content}"

    replacements = [
        ("soy ", "David es "),
        ("me llamo ", "David se llama "),
        ("tengo ", "David tiene "),
        ("vivo ", "David vive "),
        ("mi ", "su "),
        ("me gusta ", "a David le gusta "),
        ("me gustan ", "a David le gustan "),
    ]
    content_lower = content.lower()
    for old, new in replacements:
        if content_lower.startswith(old):
            content = new + content[len(old) :]
            break

    # Limpiar domain null
    if domain in ("null", "none", ""):
        domain = "general"

    return _save(content, domain, category)


def search_memory(query: str = "", domain: str | None = None) -> str:
    if domain in ("null", "none", ""):
        domain = None

    # Si hay domain específico, ignorar el query y traer todo del domain
    if domain:
        query = ""

    # Normalizar queries de identidad
    identity_queries = ["quien", "quién", "soy", "dan", "david"]
    if any(q in (query or "").lower() for q in identity_queries):
        query = ""

    results = _search(query, domain=domain, limit=8)
    if not results:
        return "No recuerdo nada sobre eso."
    lines = [f"- [{m['domain']}] {m['content']}" for m in results]
    return "Recuerdo:\n" + "\n".join(lines)


def forget_memory(query: str, domain: str | None = None) -> str:
    if not query.strip():
        return "¿Qué quieres que olvide?"
    if domain in ("null", "none", ""):
        domain = None
    return _forget(query, domain=domain)


def list_memories(domain: str | None = None) -> str:
    if domain in ("null", "none", ""):
        domain = None
    results = _search("", domain=domain, limit=10)
    if not results:
        return "No tengo recuerdos guardados."
    lines = [f"- [{m['domain']}] {m['content']}" for m in results]
    return f"Mis recuerdos ({len(results)}):\n" + "\n".join(lines)
