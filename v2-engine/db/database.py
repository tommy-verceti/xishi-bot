"""SQLite database initialization and connection management."""

import os
import aiosqlite

from config import CONFIG

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    qq_id           TEXT NOT NULL UNIQUE,
    nickname        TEXT,
    preferred_name  TEXT,
    first_seen      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen       TIMESTAMP,
    total_messages  INTEGER DEFAULT 0,
    is_active       INTEGER DEFAULT 1,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER REFERENCES users(id),
    direction       TEXT NOT NULL CHECK(direction IN ('inbound','outbound','proactive')),
    content         TEXT NOT NULL,
    raw_payload     TEXT,
    has_sticker     INTEGER DEFAULT 0,
    sticker_id      INTEGER REFERENCES stickers(id),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id, created_at);

CREATE TABLE IF NOT EXISTS memory_facts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER REFERENCES users(id),
    fact            TEXT NOT NULL,
    source_msg_id   INTEGER REFERENCES messages(id),
    confidence      REAL DEFAULT 1.0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed   TIMESTAMP,
    access_count    INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS memory_insights (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER REFERENCES users(id),
    category        TEXT NOT NULL,
    insight         TEXT NOT NULL,
    evidence_count  INTEGER DEFAULT 1,
    confidence      REAL DEFAULT 0.5,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversation_summaries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER REFERENCES users(id),
    summary         TEXT NOT NULL,
    msg_range_start INTEGER REFERENCES messages(id),
    msg_range_end   INTEGER REFERENCES messages(id),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS emotions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER REFERENCES users(id) UNIQUE,
    favorability    REAL DEFAULT 0.1,
    current_mood    TEXT DEFAULT 'calm',
    mood_intensity  REAL DEFAULT 0.5,
    mood_updated_at TIMESTAMP,
    last_mood_transition TEXT,
    total_interactions   INTEGER DEFAULT 0,
    positive_signals     INTEGER DEFAULT 0,
    negative_signals     INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS stickers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    file_path       TEXT NOT NULL,
    tags            TEXT,
    emotion_match   TEXT,
    usage_count     INTEGER DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type       TEXT NOT NULL CHECK(task_type IN ('timed','random','reminder')),
    cron_expression TEXT,
    min_interval_h  INTEGER,
    max_interval_h  INTEGER,
    template        TEXT,
    target_filter   TEXT,
    is_enabled      INTEGER DEFAULT 1,
    last_fired      TIMESTAMP,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS task_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id         INTEGER REFERENCES scheduled_tasks(id),
    user_id         INTEGER REFERENCES users(id),
    message_sent    TEXT,
    message_id      INTEGER REFERENCES messages(id),
    fired_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status          TEXT DEFAULT 'sent'
);
"""


async def get_db(db_path: str | None = None) -> aiosqlite.Connection:
    path = db_path or CONFIG.db_path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    db = await aiosqlite.connect(path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db(db: aiosqlite.Connection) -> None:
    await db.executescript(SCHEMA)
    await db.commit()
