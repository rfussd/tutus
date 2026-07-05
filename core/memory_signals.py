from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

log = logging.getLogger("tutus.memory_signals")

DB_PATH: Path = Path(__file__).parent.parent / "data" / "memory.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

_connection: sqlite3.Connection | None = None


def get_connection() -> sqlite3.Connection:
    global _connection
    if _connection is None:
        _connection = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _connection.row_factory = sqlite3.Row
    return _connection


def init_db() -> None:
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(domain, key)
        );

        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            created_at TEXT NOT NULL
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
        USING fts5(content, domain, category, content=memories, content_rowid=id);

        CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
            INSERT INTO memories_fts(rowid, content, domain, category)
            VALUES (new.id, new.content, new.domain, new.category);
        END;

        CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
            INSERT INTO memories_fts(memories_fts, rowid, content, domain, category)
            VALUES ('delete', old.id, old.content, old.domain, old.category);
        END;

        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            domain TEXT DEFAULT 'chat',
            created_at TEXT NOT NULL
        );
    """)
    conn.commit()


# ─────────────────────────────────────────
# SIGNALS — preferencias por dominio
# ─────────────────────────────────────────


def set_signal(domain: str, key: str, value: Any) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO signals (domain, key, value, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(domain, key) DO UPDATE SET
            value = excluded.value,
            updated_at = excluded.updated_at
    """,
        (domain, key, json.dumps(value), datetime.now().isoformat()),
    )
    conn.commit()


def get_signal(domain: str, key: str, default: Any = None) -> Any:
    conn = get_connection()
    row = conn.execute("SELECT value FROM signals WHERE domain=? AND key=?", (domain, key)).fetchone()
    if row:
        return json.loads(row["value"])
    return default


def get_domain_signals(domain: str) -> dict[str, Any]:
    conn = get_connection()
    rows = conn.execute("SELECT key, value FROM signals WHERE domain=?", (domain,)).fetchall()
    return {row["key"]: json.loads(row["value"]) for row in rows}


# ─────────────────────────────────────────
# MEMORIES — recuerdos por dominio
# ─────────────────────────────────────────


def save_memory(content: str, domain: str = "general", category: str = "general") -> str:
    conn = get_connection()
    conn.execute(
        "INSERT INTO memories (domain, content, category, created_at) VALUES (?, ?, ?, ?)",
        (domain, content, category, datetime.now().isoformat()),
    )
    conn.commit()
    return f"Recordado: {content}"


def search_memories(query: str, domain: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
    conn = get_connection()

    try:
        if query and query.strip():
            if domain:
                rows = conn.execute(
                    """
                    SELECT m.content, m.domain, m.category, m.created_at
                    FROM memories_fts f
                    JOIN memories m ON m.id = f.rowid
                    WHERE memories_fts MATCH ? AND m.domain = ?
                    ORDER BY rank LIMIT ?
                """,
                    (query, domain, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT m.content, m.domain, m.category, m.created_at
                    FROM memories_fts f
                    JOIN memories m ON m.id = f.rowid
                    WHERE memories_fts MATCH ?
                    ORDER BY rank LIMIT ?
                """,
                    (query, limit),
                ).fetchall()
        else:
            if domain:
                rows = conn.execute(
                    """
                    SELECT content, domain, category, created_at
                    FROM memories WHERE domain=?
                    ORDER BY created_at DESC LIMIT ?
                """,
                    (domain, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT content, domain, category, created_at
                    FROM memories ORDER BY created_at DESC LIMIT ?
                """,
                    (limit,),
                ).fetchall()
    except Exception as e:
        log.debug("Memory search error: %s", e)
        rows = conn.execute(
            "SELECT content, domain, category, created_at FROM memories ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()

    return [dict(r) for r in rows]


def forget_memories(query: str, domain: str | None = None) -> str:
    conn = get_connection()
    if domain:
        deleted = conn.execute("DELETE FROM memories WHERE content LIKE ? AND domain=?", (f"%{query}%", domain)).rowcount
    else:
        deleted = conn.execute("DELETE FROM memories WHERE content LIKE ?", (f"%{query}%",)).rowcount
    conn.commit()
    return f"Olvidé {deleted} recuerdos sobre '{query}'"


def get_context_for_domain(domain: str) -> str:
    signals = get_domain_signals(domain)
    memories = search_memories("", domain=domain, limit=3)

    context = []

    if signals:
        sig_lines = [f"  - {k}: {v}" for k, v in signals.items()]
        context.append("Preferencias:\n" + "\n".join(sig_lines))

    if memories:
        mem_lines = [f"  - {m['content']}" for m in memories]
        context.append("Recuerdos relevantes:\n" + "\n".join(mem_lines))

    return "\n".join(context) if context else ""


# ─────────────────────────────────────────
# CONVERSATIONS — historial para fine-tuning
# ─────────────────────────────────────────


def log_conversation(role: str, content: str, domain: str = "chat") -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO conversations (role, content, domain, created_at) VALUES (?, ?, ?, ?)",
        (role, content, domain, datetime.now().isoformat()),
    )
    conn.commit()


def get_conversations(limit: int = 500, domain: str | None = None) -> list[dict[str, Any]]:
    conn = get_connection()
    if domain:
        rows = conn.execute(
            "SELECT role, content, domain, created_at FROM conversations WHERE domain=? ORDER BY id ASC LIMIT ?", (domain, limit)
        ).fetchall()
    else:
        rows = conn.execute("SELECT role, content, domain, created_at FROM conversations ORDER BY id ASC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def export_conversations_for_training(output_path: str | None = None, limit: int = 500) -> str:
    import json

    convos = get_conversations(limit=limit)
    if not convos:
        return "No hay conversaciones guardadas."

    pairs = []
    current = []
    for c in convos:
        current.append(c)
        if c["role"] == "assistant" and len(current) >= 2:
            user_msg = next((x["content"] for x in current if x["role"] == "user"), "")
            asst_msg = c["content"]
            if user_msg and asst_msg:
                pairs.append({"instruction": user_msg, "response": asst_msg})
            current = [c]

    if not output_path:
        from pathlib import Path

        output_path = str(Path(__file__).parent.parent / "training" / "conversations.jsonl")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    return f"Exportadas {len(pairs)} conversaciones a {output_path}"


# Inicializar DB al importar
init_db()
