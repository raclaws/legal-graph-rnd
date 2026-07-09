"""Graph service — SQLite queries for the API."""

from __future__ import annotations

import sqlite3
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent.parent / "data" / "legal.db"


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def get_provision(node_id: str) -> dict | None:
    try:
        db = _get_db()

        row = db.execute(
            "SELECT node_id, type, number, title, text, parent_id FROM provisions WHERE node_id = ?",
            (node_id,),
        ).fetchone()

        if not row:
            parts = node_id.split("/")
            if len(parts) >= 3:
                reg_prefix = "/".join(parts[:3])
                rest = "/" + "/".join(parts[3:])
                pasal_idx = rest.find("/Pasal/")
                pasal_part = rest[pasal_idx:] if pasal_idx >= 0 else ""
                if pasal_part:
                    row = db.execute(
                        "SELECT node_id, type, number, title, text, parent_id FROM provisions "
                        "WHERE node_id LIKE ? AND node_id LIKE ? LIMIT 1",
                        (f"{reg_prefix}%", f"%{pasal_part}"),
                    ).fetchone()

        if not row:
            db.close()
            return None

        children = db.execute(
            "SELECT node_id, type, number, text FROM provisions WHERE parent_id = ?",
            (row["node_id"],),
        ).fetchall()

        norms = db.execute(
            "SELECT id, description, severity FROM norms WHERE provision_id = ?",
            (row["node_id"],),
        ).fetchall()

        result = {
            "node_id": row["node_id"],
            "type": row["type"],
            "number": row["number"] or "",
            "text": row["text"],
            "parent": row["parent_id"],
            "children": [
                {"node_id": c["node_id"], "type": c["type"], "number": c["number"] or "", "text": c["text"]}
                for c in children
            ],
            "norms_derived": [
                {"id": n["id"], "description": n["description"], "severity": n["severity"]}
                for n in norms
            ],
        }
        db.close()
        return result
    except Exception:
        return None


def validate_citations(node_ids: list[str]) -> dict[str, bool]:
    if not node_ids:
        return {}

    results = {nid: False for nid in node_ids}

    try:
        db = _get_db()
        for nid in node_ids:
            row = db.execute(
                "SELECT 1 FROM provisions WHERE node_id = ? LIMIT 1", (nid,)
            ).fetchone()
            if row:
                results[nid] = True
                continue

            parts = nid.split("/")
            if len(parts) >= 3:
                reg_prefix = "/".join(parts[:3])
                rest = "/" + "/".join(parts[3:])
                pasal_idx = rest.find("/Pasal/")
                pasal_part = rest[pasal_idx:] if pasal_idx >= 0 else ""
                if pasal_part:
                    row = db.execute(
                        "SELECT 1 FROM provisions WHERE node_id LIKE ? AND node_id LIKE ? LIMIT 1",
                        (f"{reg_prefix}%", f"%{pasal_part}"),
                    ).fetchone()
                    if row:
                        results[nid] = True
        db.close()
    except Exception:
        pass

    return results


def get_graph_stats() -> dict:
    try:
        db = _get_db()
        provisions = db.execute("SELECT count(*) FROM provisions").fetchone()[0]
        regulations = db.execute("SELECT count(*) FROM regulations").fetchone()[0]
        norms = db.execute("SELECT count(*) FROM norms").fetchone()[0]
        db.close()
        return {"provisions": provisions, "regulations": regulations, "norms": norms}
    except Exception:
        return {"provisions": 0, "regulations": 0, "norms": 0}


def search_definitions(keywords: list[str], limit: int = 10) -> list[dict]:
    if not keywords:
        return []

    try:
        db = _get_db()
        fts_query = " OR ".join(keywords)
        rows = db.execute(
            """SELECT p.node_id, p.text, p.number, p.type,
                      CASE
                        WHEN p.number = '1' THEN 3
                        WHEN p.text LIKE '%yang dimaksud dengan%' THEN 2
                        WHEN p.text LIKE '%ketentuan umum%' THEN 2
                        ELSE 1
                      END AS priority
               FROM provisions_fts f
               JOIN provisions p ON p.node_id = f.node_id
               WHERE provisions_fts MATCH ?
               ORDER BY priority DESC, length(p.text) ASC
               LIMIT ?""",
            (fts_query, limit),
        ).fetchall()

        results = [
            {"node_id": r["node_id"], "text": r["text"], "number": r["number"], "type": r["type"]}
            for r in rows
        ]
        db.close()
        return results
    except Exception:
        return []


def search_provisions_by_topic(keywords: list[str], limit: int = 15) -> list[dict]:
    if not keywords:
        return []

    try:
        db = _get_db()
        fts_query = " OR ".join(keywords)
        rows = db.execute(
            """SELECT p.node_id, p.text
               FROM provisions_fts f
               JOIN provisions p ON p.node_id = f.node_id
               WHERE provisions_fts MATCH ?
               ORDER BY length(p.text) ASC
               LIMIT ?""",
            (fts_query, limit),
        ).fetchall()

        results = [
            {"node_id": r["node_id"], "text": (r["text"] or "")[:300]}
            for r in rows
        ]
        db.close()
        return results
    except Exception:
        return []
