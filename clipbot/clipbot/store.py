"""SQLite log of every clip the bot makes and where it was posted."""
from __future__ import annotations

import sqlite3
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS clips (
    clip_id     TEXT PRIMARY KEY,
    channel     TEXT NOT NULL,
    created_at  REAL NOT NULL,
    reason      TEXT,
    clip_url    TEXT,
    video_path  TEXT,
    caption     TEXT,
    publish_id  TEXT,
    status      TEXT,
    error       TEXT
);
"""


class Store:
    def __init__(self, path: str):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute(SCHEMA)
        self.db.commit()

    def add(self, clip_id: str, channel: str, reason: str) -> None:
        self.db.execute("INSERT OR IGNORE INTO clips (clip_id, channel, created_at, reason, status) "
                        "VALUES (?, ?, ?, ?, 'created')", (clip_id, channel, time.time(), reason))
        self.db.commit()

    def update(self, clip_id: str, **fields) -> None:
        cols = ", ".join(f"{k} = ?" for k in fields)
        self.db.execute(f"UPDATE clips SET {cols} WHERE clip_id = ?", (*fields.values(), clip_id))
        self.db.commit()

    def posts_last_24h(self) -> int:
        row = self.db.execute("SELECT COUNT(*) FROM clips WHERE publish_id IS NOT NULL AND created_at > ?",
                              (time.time() - 86400,)).fetchone()
        return row[0]

    def recent(self, limit: int = 20) -> list[tuple]:
        return self.db.execute("SELECT created_at, channel, reason, status, clip_url, error FROM clips "
                               "ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
