"""Persistent shared idea storage for the web UI."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class Idea:
    id: int
    text: str
    score: int
    votes_up: int
    votes_down: int
    created_at: str
    author_label: str


class IdeaStore:
    """SQLite-backed storage for shared ideas."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ideas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    score INTEGER NOT NULL DEFAULT 0,
                    votes_up INTEGER NOT NULL DEFAULT 0,
                    votes_down INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    author_label TEXT NOT NULL,
                    author_ip TEXT,
                    user_agent TEXT
                )
                """
            )

    def list_ideas(self) -> list[Idea]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, text, score, votes_up, votes_down, created_at, author_label
                FROM ideas
                ORDER BY score DESC, id DESC
                """
            ).fetchall()
        return [Idea(**dict(row)) for row in rows]

    def create_idea(self, text: str, author_label: str, author_ip: str | None, user_agent: str | None) -> Idea:
        created_at = datetime.now(UTC).isoformat(timespec="seconds")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO ideas (text, created_at, author_label, author_ip, user_agent)
                VALUES (?, ?, ?, ?, ?)
                """,
                (text, created_at, author_label, author_ip, user_agent),
            )
            idea_id = int(cursor.lastrowid)
            row = connection.execute(
                """
                SELECT id, text, score, votes_up, votes_down, created_at, author_label
                FROM ideas
                WHERE id = ?
                """,
                (idea_id,),
            ).fetchone()
        return Idea(**dict(row))

    def vote(self, idea_id: int, delta: int) -> Idea | None:
        if delta not in {-1, 1}:
            raise ValueError("Vote delta must be -1 or 1.")

        with self._connect() as connection:
            row = connection.execute(
                "SELECT id FROM ideas WHERE id = ?",
                (idea_id,),
            ).fetchone()
            if row is None:
                return None

            if delta > 0:
                connection.execute(
                    """
                    UPDATE ideas
                    SET votes_up = votes_up + 1,
                        score = score + 1
                    WHERE id = ?
                    """,
                    (idea_id,),
                )
            else:
                connection.execute(
                    """
                    UPDATE ideas
                    SET votes_down = votes_down + 1,
                        score = score - 1
                    WHERE id = ?
                    """,
                    (idea_id,),
                )

            updated = connection.execute(
                """
                SELECT id, text, score, votes_up, votes_down, created_at, author_label
                FROM ideas
                WHERE id = ?
                """,
                (idea_id,),
            ).fetchone()

        return Idea(**dict(updated)) if updated is not None else None
