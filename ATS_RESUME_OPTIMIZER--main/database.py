"""
database.py — Lightweight SQLite persistence for Career Forge.

Everything in the app previously lived in Streamlit session_state and vanished
on refresh. This module stores a durable history of ATS scores and generated
artifacts so users can track progress over time. It is intentionally tiny and
dependency-free (sqlite3 ships with Python).
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "career_forge.db")


@contextmanager
def _conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db() -> None:
    with _conn() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS score_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at  TEXT NOT NULL,
                candidate   TEXT,
                company     TEXT,
                role        TEXT,
                mode        TEXT,
                score       INTEGER,
                delta       INTEGER,
                detail      TEXT
            )
            """
        )


def log_score(candidate: str = "", company: str = "", role: str = "",
              mode: str = "analysis", score: int = 0, delta: int = 0,
              detail: str = "") -> None:
    """Record a scoring event."""
    init_db()
    with _conn() as con:
        con.execute(
            "INSERT INTO score_history "
            "(created_at, candidate, company, role, mode, score, delta, detail) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (datetime.now().isoformat(timespec="seconds"), candidate, company,
             role, mode, int(score), int(delta), detail),
        )


def get_history(limit: int = 100) -> list:
    """Return recent scoring events as a list of dicts (newest first)."""
    init_db()
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM score_history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def clear_history() -> None:
    with _conn() as con:
        con.execute("DELETE FROM score_history")
