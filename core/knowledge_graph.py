from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import threading
from datetime import datetime
from typing import Any

import networkx as nx

log = logging.getLogger("tutus.knowledge_graph")


DB_PATH: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "knowledge.db")
EXTRACTION_PROMPT: str = """Extrae conocimiento en formato triples (sujeto, predicado, objeto) del siguiente texto.
Reglas:
- Solo extrae hechos concretos y explícitos
- Sujeto y objeto deben ser entidades nombradas (personas, proyectos, tecnologías, lugares, etc.)
- Predicado debe ser una relación simple: "es", "trabaja_en", "jefe_de", "dijo", "creó", "usa", "tiene", "planea", "gusta", "odio", "quiere"
- Ignora opiniones vagas, preguntas, negaciones
- Responde SOLO con JSON array: [["sujeto", "predicado", "objeto"], ...]
- Si no hay hechos extraíbles, responde []

Texto: {{TEXT}}"""


class KnowledgeGraph:
    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path: str = db_path
        self._lock: threading.Lock = threading.Lock()
        self._graph: nx.MultiDiGraph = nx.MultiDiGraph()
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
        self._load_graph()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS triples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object TEXT NOT NULL,
                    context TEXT,
                    source TEXT,
                    timestamp TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0
                );
                CREATE INDEX IF NOT EXISTS idx_subject ON triples(subject);
                CREATE INDEX IF NOT EXISTS idx_object ON triples(object);
                CREATE INDEX IF NOT EXISTS idx_predicate ON triples(predicate);
            """)

    def _load_graph(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT subject, predicate, object, context, source, timestamp, confidence FROM triples").fetchall()
        for row in rows:
            s, p, o, ctx, src, ts, conf = row
            self._graph.add_edge(s, o, key=ts, predicate=p, context=ctx, source=src, timestamp=ts, confidence=conf)

    def add_triple(
        self, subject: str, predicate: str, object_: str, context: str = "", source: str = "manual", confidence: float = 1.0
    ) -> None:
        subject = subject.strip().lower()
        predicate = predicate.strip().lower()
        object_ = object_.strip().lower()
        timestamp = datetime.now().isoformat()

        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO triples (subject, predicate, object, context, source, timestamp, confidence) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (subject, predicate, object_, context, source, timestamp, confidence),
                )
            self._graph.add_edge(
                subject,
                object_,
                key=timestamp,
                predicate=predicate,
                context=context,
                source=source,
                timestamp=timestamp,
                confidence=confidence,
            )

    def get_entity_info(self, entity: str) -> list[dict[str, Any]]:
        entity = entity.strip().lower()
        results = []
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT subject, predicate, object, context, timestamp, confidence FROM triples WHERE subject = ? OR object = ? ORDER BY timestamp DESC LIMIT 50",
                (entity, entity),
            ).fetchall()
        for row in rows:
            s, p, o, ctx, ts, conf = row
            if s == entity:
                results.append({"relation": p, "target": o, "direction": "out", "context": ctx, "timestamp": ts, "confidence": conf})
            if o == entity:
                results.append({"relation": p, "source": s, "direction": "in", "context": ctx, "timestamp": ts, "confidence": conf})
        return results

    def query_relation(self, subject: str, predicate: str) -> list[str]:
        subject = subject.strip().lower()
        predicate = predicate.strip().lower()
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT object FROM triples WHERE subject = ? AND predicate = ? ORDER BY timestamp DESC",
                (subject, predicate),
            ).fetchall()
        return [r[0] for r in rows]

    def query_entities_by_relation(self, predicate: str, object_: str) -> list[str]:
        object_ = object_.strip().lower()
        predicate = predicate.strip().lower()
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT subject FROM triples WHERE predicate = ? AND object = ? ORDER BY timestamp DESC",
                (predicate, object_),
            ).fetchall()
        return [r[0] for r in rows]

    def get_recent_context(self, entity: str, days: int = 7) -> str:
        entity = entity.strip().lower()
        from datetime import timedelta

        since = (datetime.now() - timedelta(days=days)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT context, timestamp FROM triples WHERE (subject = ? OR object = ?) AND timestamp > ? AND context != '' ORDER BY timestamp DESC LIMIT 10",
                (entity, entity, since),
            ).fetchall()
        return "\n".join(f"[{r[1][:10]}] {r[0]}" for r in rows)

    def search_entities(self, query: str) -> list[str]:
        query = query.strip().lower()
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT DISTINCT subject FROM triples WHERE subject LIKE ? UNION SELECT DISTINCT object FROM triples WHERE object LIKE ? LIMIT 20",
                (f"%{query}%", f"%{query}%"),
            ).fetchall()
        return list(set(r[0] for r in rows))

    def fmt_entity_info(self, entity: str) -> str:
        info = self.get_entity_info(entity)
        if not info:
            return f"No tengo información sobre '{entity}'."
        lines = [f"[{entity.title()}]"]
        for item in info:
            if item["direction"] == "out":
                lines.append(f"  - {item['relation']}: {item['target']}")
            else:
                lines.append(f"  - es {item['relation']} de: {item['source']}")
        return "\n".join(lines)

    def add_triples_from_text(self, text: str, use_llm: bool = True) -> list[list[str]]:
        triples = self._extract_patterns(text)
        if use_llm and not triples:
            triples = self._extract_with_llm(text)
        for s, p, o in triples:
            self.add_triple(s, p, o, context=text[:200], source="llm")
        return triples

    def _extract_patterns(self, text: str) -> list[list[str]]:
        text_clean = re.sub(r"\b(y|e|pero|además|también)\b", ".", text.lower())
        patterns = [
            (r"(?:mi\s+)?(\w[\w\s]*?)\s+(?:es|se llama)\s+(.+?)(?:\.|,|$)", "es"),
            (r"(\w[\w\s]*?)\s+trabaja\s+(?:en|para|con)\s+(.+?)(?:\.|,|$)", "trabaja_en"),
            (r"(?:mi|el|la)\s+jefe\s*(?:a)?\s+(?:de\s+)?(\w[\w\s]*?)?\s*(?:es|se llama)\s+(.+?)(?:\.|,|$)", "jefe_de"),
            (r"(\w[\w\s]*?)\s+(?:dijo|menciono|comento)\s+que\s+(.+?)(?:\.|,|$)", "dijo"),
            (r"(\w[\w\s]*?)\s+(?:usa|utiliza|ocupa)\s+(.+?)(?:\.|,|$)", "usa"),
            (r"(\w[\w\s]*?)\s+(?:creo|hizo|desarrollo)\s+(.+?)(?:\.|,|$)", "creo"),
            (r"(\w[\w\s]*?)\s+(?:tiene|posee)\s+(.+?)(?:\.|,|$)", "tiene"),
            (r"(\w[\w\s]*?)\s+(?:planea|quiere|va a)\s+(.+?)(?:\.|,|$)", "planea"),
            (r"(?:me\s+)?(?:gusta|encanta|amo)\s+(.+?)(?:\.|,|$)", "gusta"),
            (r"(?:no\s+)?(?:odio|detesto|molesta)\s+(.+?)(?:\.|,|$)", "odia"),
        ]
        results = []
        for pattern, predicate in patterns:
            matches = re.findall(pattern, text_clean)
            for m in matches:
                if isinstance(m, tuple) and len(m) == 2:
                    s, o = m[0].strip(), m[1].strip()
                    if s and o and s != o and len(s.split()) <= 4 and len(o.split()) <= 8:
                        results.append([s, predicate, o])
                elif isinstance(m, str):
                    results.append(["yo", predicate, m.strip()])
        return results

    def _extract_with_llm(self, text: str) -> list[list[str]]:
        try:
            import requests

            from core.config import LM_STUDIO_URL, MODEL_ID

            prompt = EXTRACTION_PROMPT.replace("{{TEXT}}", text)
            resp = requests.post(
                LM_STUDIO_URL,
                json={
                    "model": MODEL_ID,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 512,
                },
                timeout=30,
            )
            raw = resp.json()["choices"][0]["message"]["content"].strip()
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start >= 0 and end > start:
                triples = json.loads(raw[start:end])
                if isinstance(triples, list):
                    return [t for t in triples if len(t) == 3]
        except Exception as e:
            log.debug("[KnowledgeGraph] LLM extraction error: %s", e)
        return []

    def get_all_entities(self) -> list[str]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT DISTINCT subject FROM triples UNION SELECT DISTINCT object FROM triples").fetchall()
        return sorted(set(r[0] for r in rows))

    def get_stats(self) -> dict[str, int]:
        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM triples").fetchone()[0]
            entities = conn.execute(
                "SELECT COUNT(DISTINCT e) FROM (SELECT subject AS e FROM triples UNION SELECT object AS e FROM triples)"
            ).fetchone()[0]
        return {"triples": count, "entities": entities}

    def get_graph_insights(self) -> str:
        stats = self.get_stats()
        top_entities = sorted(self._graph.degree(), key=lambda x: x[1], reverse=True)[:10]
        lines = [f"[KG] Knowledge Graph: {stats['triples']} hechos, {stats['entities']} entidades"]
        if top_entities:
            lines.append("Entidades mas conectadas:")
            for ent, deg in top_entities:
                lines.append(f"  - {ent.title()} ({deg} conexiones)")
        return "\n".join(lines)


_knowledge_graph: KnowledgeGraph | None = None


def get_knowledge_graph() -> KnowledgeGraph:
    global _knowledge_graph
    if _knowledge_graph is None:
        _knowledge_graph = KnowledgeGraph()
    return _knowledge_graph
