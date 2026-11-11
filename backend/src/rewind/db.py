"""
SQLite storage.

One short-lived connection per unit of work (`with db.tx() as conn:`): cheap
with SQLite, and safe with FastAPI's thread pool. WAL mode lets the TV UI read
while a background job writes.

Schema changes are numbered migrations tracked with `PRAGMA user_version`.
"""

from __future__ import annotations

import json
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

MIGRATIONS: list[str] = [
    # 1 — initial schema
    """
    CREATE TABLE kv (
        key        TEXT PRIMARY KEY,
        value      TEXT NOT NULL,          -- JSON
        updated_at INTEGER NOT NULL
    );

    -- YouTube progress, keyed by playlist (follows the content, not the channel slot).
    CREATE TABLE playlist_progress (
        playlist_id TEXT PRIMARY KEY,
        video_id    TEXT NOT NULL,
        video_index INTEGER NOT NULL DEFAULT 0,
        position    REAL NOT NULL DEFAULT 0,
        updated_at  INTEGER NOT NULL
    );
    CREATE TABLE video_progress (
        playlist_id TEXT NOT NULL,
        video_id    TEXT NOT NULL,
        position    REAL NOT NULL DEFAULT 0,
        updated_at  INTEGER NOT NULL,
        PRIMARY KEY (playlist_id, video_id)
    );

    -- Movies, series, episodes and download packs.
    CREATE TABLE media (
        id             TEXT PRIMARY KEY,
        kind           TEXT NOT NULL CHECK (kind IN ('movie', 'series', 'episode', 'pack')),
        parent_id      TEXT REFERENCES media(id) ON DELETE CASCADE,
        title          TEXT NOT NULL,
        year           INTEGER,
        season         INTEGER,
        episode        INTEGER,
        status         TEXT NOT NULL,
        file           TEXT,                 -- relative to the media dir
        duration       REAL NOT NULL DEFAULT 0,
        position       REAL NOT NULL DEFAULT 0,
        watched        INTEGER NOT NULL DEFAULT 0,
        last_played_at INTEGER,
        added_at       INTEGER NOT NULL,
        data           TEXT NOT NULL DEFAULT '{}'  -- JSON: metadata, subtitles, job state…
    );
    CREATE INDEX media_parent ON media(parent_id);
    CREATE INDEX media_kind ON media(kind);

    CREATE TABLE advisor_blacklist (
        id       TEXT PRIMARY KEY,
        title    TEXT NOT NULL,
        year     INTEGER,
        added_at INTEGER NOT NULL
    );
    """,
]

MEDIA_COLUMNS = (
    "id", "kind", "parent_id", "title", "year", "season", "episode", "status", "file",
    "duration", "position", "watched", "last_played_at", "added_at",
)  # fmt: skip


def now() -> int:
    return int(time.time())


class Database:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.tx() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
        self.migrate()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            with conn:  # commit on success, rollback on error
                yield conn
        finally:
            conn.close()

    def migrate(self) -> int:
        with self.tx() as conn:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            for i, script in enumerate(MIGRATIONS[version:], start=version + 1):
                conn.executescript(f"BEGIN; {script}; PRAGMA user_version = {i}; COMMIT;")
            return conn.execute("PRAGMA user_version").fetchone()[0]

    # --- key/value state ----------------------------------------------------

    def get_kv(self, key: str, default: Any = None) -> Any:
        with self.tx() as conn:
            row = conn.execute("SELECT value FROM kv WHERE key = ?", (key,)).fetchone()
        return json.loads(row["value"]) if row else default

    def set_kv(self, key: str, value: Any) -> None:
        with self.tx() as conn:
            conn.execute(
                "INSERT INTO kv (key, value, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
                "updated_at = excluded.updated_at",
                (key, json.dumps(value), now()),
            )

    # --- YouTube progress ---------------------------------------------------

    def get_playlist_progress(self, playlist_id: str) -> dict | None:
        with self.tx() as conn:
            row = conn.execute(
                "SELECT * FROM playlist_progress WHERE playlist_id = ?", (playlist_id,)
            ).fetchone()
            if not row:
                return None
            videos = conn.execute(
                "SELECT video_id, position, updated_at FROM video_progress WHERE playlist_id = ?",
                (playlist_id,),
            ).fetchall()
        return {
            "video_id": row["video_id"],
            "video_index": row["video_index"],
            "position": row["position"],
            "updated_at": row["updated_at"],
            "videos": {v["video_id"]: v["position"] for v in videos},
        }

    def save_playlist_progress(
        self,
        playlist_id: str,
        video_id: str,
        video_index: int,
        position: float,
        updated_at: int | None = None,
    ) -> None:
        ts = updated_at or now()
        with self.tx() as conn:
            conn.execute(
                "INSERT INTO playlist_progress VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(playlist_id) DO UPDATE SET video_id = excluded.video_id, "
                "video_index = excluded.video_index, position = excluded.position, "
                "updated_at = excluded.updated_at",
                (playlist_id, video_id, video_index, position, ts),
            )
            conn.execute(
                "INSERT INTO video_progress VALUES (?, ?, ?, ?) "
                "ON CONFLICT(playlist_id, video_id) DO UPDATE SET "
                "position = excluded.position, updated_at = excluded.updated_at",
                (playlist_id, video_id, position, ts),
            )

    def save_video_progress(
        self, playlist_id: str, video_id: str, position: float, updated_at: int
    ) -> None:
        with self.tx() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO video_progress VALUES (?, ?, ?, ?)",
                (playlist_id, video_id, position, updated_at),
            )

    # --- media --------------------------------------------------------------

    @staticmethod
    def _media_row(row: sqlite3.Row) -> dict:
        item = {k: row[k] for k in MEDIA_COLUMNS}
        item["watched"] = bool(item["watched"])
        item.update(json.loads(row["data"]))
        return item

    def list_media(self, kind: str | None = None, parent_id: str | None = None) -> list[dict]:
        sql, args = "SELECT * FROM media WHERE 1 = 1", []
        if kind:
            sql += " AND kind = ?"
            args.append(kind)
        if parent_id:
            sql += " AND parent_id = ?"
            args.append(parent_id)
        with self.tx() as conn:
            rows = conn.execute(sql + " ORDER BY added_at DESC", args).fetchall()
        return [self._media_row(r) for r in rows]

    def get_media(self, media_id: str) -> dict | None:
        with self.tx() as conn:
            row = conn.execute("SELECT * FROM media WHERE id = ?", (media_id,)).fetchone()
        return self._media_row(row) if row else None

    def upsert_media(self, item: dict, conn: sqlite3.Connection | None = None) -> None:
        """Insert or replace a media item. Unknown keys go to the JSON `data` column."""
        cols = {k: item.get(k) for k in MEDIA_COLUMNS}
        cols["watched"] = int(bool(cols["watched"]))
        cols["duration"] = cols["duration"] or 0
        cols["position"] = cols["position"] or 0
        cols["added_at"] = cols["added_at"] or now()
        data = {k: v for k, v in item.items() if k not in MEDIA_COLUMNS}
        # A real UPSERT, not INSERT OR REPLACE: REPLACE deletes the row first,
        # which would cascade-delete a series' episodes.
        updates = ", ".join(f"{c} = excluded.{c}" for c in (*MEDIA_COLUMNS[1:], "data"))
        sql = (
            f"INSERT INTO media ({', '.join(MEDIA_COLUMNS)}, data) "
            f"VALUES ({', '.join('?' * len(MEDIA_COLUMNS))}, ?) "
            f"ON CONFLICT(id) DO UPDATE SET {updates}"
        )
        args = [*cols.values(), json.dumps(data, ensure_ascii=False)]
        if conn is not None:
            conn.execute(sql, args)
        else:
            with self.tx() as c:
                c.execute(sql, args)

    def patch_media(self, media_id: str, fields: dict) -> dict | None:
        """Update some fields of an item (columns or JSON data)."""
        with self.tx() as conn:
            row = conn.execute("SELECT * FROM media WHERE id = ?", (media_id,)).fetchone()
            if not row:
                return None
            item = self._media_row(row)
            item.update(fields)
            self.upsert_media(item, conn)
        return item

    # --- advisor blacklist --------------------------------------------------

    def blacklist_add(self, item_id: str, title: str, year: int | None, added_at: int) -> None:
        with self.tx() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO advisor_blacklist VALUES (?, ?, ?, ?)",
                (item_id, title, year, added_at),
            )

    def blacklist(self) -> list[dict]:
        with self.tx() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM advisor_blacklist")]
