"""CRUD operations for users, facts, messages, and emotions.

Phase 1: users + memory_facts + messages tables.
Phase 2: emotions table.
"""

from datetime import UTC, datetime
from typing import Any

import aiosqlite
from config import CONFIG

# ── Users (L1) ──────────────────────────────────────────────


async def get_or_create_user(
    db: aiosqlite.Connection, qq_id: str
) -> dict[str, Any]:
    rows = await db.execute_fetchall(
        "SELECT * FROM users WHERE qq_id = ?", (qq_id,)
    )
    if rows:
        user = dict(rows[0])
        await db.execute(
            "UPDATE users SET last_seen = ?, total_messages = total_messages + 1 "
            "WHERE id = ?",
            (datetime.now(UTC), user["id"]),
        )
        await db.commit()
        user["total_messages"] += 1
        return user

    await db.execute(
        "INSERT INTO users (qq_id, first_seen, last_seen, total_messages) "
        "VALUES (?, ?, ?, 1)",
        (qq_id, datetime.now(UTC), datetime.now(UTC)),
    )
    await db.commit()
    rows = await db.execute_fetchall(
        "SELECT * FROM users WHERE qq_id = ?", (qq_id,)
    )
    return dict(rows[0])


async def update_user_preference(
    db: aiosqlite.Connection, user_id: int, field: str, value: str
) -> None:
    valid = {"nickname", "preferred_name", "notes"}
    if field not in valid:
        raise ValueError(f"Invalid field: {field}")
    await db.execute(
        f"UPDATE users SET {field} = ? WHERE id = ?", (value, user_id)
    )
    await db.commit()


async def get_active_users(db: aiosqlite.Connection) -> list[dict[str, Any]]:
    rows = await db.execute_fetchall(
        "SELECT * FROM users WHERE is_active = 1 ORDER BY last_seen DESC"
    )
    return [dict(r) for r in rows]


# ── Messages ────────────────────────────────────────────────


async def store_message(
    db: aiosqlite.Connection,
    user_id: int,
    direction: str,
    content: str,
    raw_payload: str | None = None,
    has_sticker: int = 0,
    sticker_id: int | None = None,
) -> int:
    cursor = await db.execute(
        "INSERT INTO messages "
        "(user_id, direction, content, raw_payload, has_sticker, sticker_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, direction, content, raw_payload, has_sticker, sticker_id),
    )
    await db.commit()
    return cursor.lastrowid


async def get_message_count(db: aiosqlite.Connection, user_id: int) -> int:
    rows = await db.execute_fetchall(
        "SELECT COUNT(*) as cnt FROM messages WHERE user_id = ?", (user_id,)
    )
    return rows[0]["cnt"] if rows else 0


async def get_recent_messages(
    db: aiosqlite.Connection, user_id: int, limit: int = 50
) -> list[dict[str, Any]]:
    rows = await db.execute_fetchall(
        "SELECT * FROM messages WHERE user_id = ? "
        "ORDER BY created_at DESC LIMIT ?",
        (user_id, limit),
    )
    return [dict(r) for r in reversed(rows)]


# ── Memory Facts (L2) ───────────────────────────────────────


async def store_fact(
    db: aiosqlite.Connection,
    user_id: int,
    fact: str,
    source_msg_id: int | None = None,
) -> int:
    cursor = await db.execute(
        "INSERT INTO memory_facts (user_id, fact, source_msg_id) "
        "VALUES (?, ?, ?)",
        (user_id, fact, source_msg_id),
    )
    await db.commit()
    return cursor.lastrowid


async def get_facts(
    db: aiosqlite.Connection, user_id: int
) -> list[dict[str, Any]]:
    rows = await db.execute_fetchall(
        "SELECT * FROM memory_facts WHERE user_id = ? "
        "ORDER BY last_accessed DESC, access_count DESC",
        (user_id,),
    )
    return [dict(r) for r in rows]


async def delete_facts(
    db: aiosqlite.Connection, user_id: int, keyword: str
) -> int:
    cursor = await db.execute(
        "DELETE FROM memory_facts WHERE user_id = ? AND fact LIKE ?",
        (user_id, f"%{keyword}%"),
    )
    await db.commit()
    return cursor.rowcount


async def _touch_fact(db: aiosqlite.Connection, fact_id: int) -> None:
    await db.execute(
        "UPDATE memory_facts "
        "SET last_accessed = ?, access_count = access_count + 1 "
        "WHERE id = ?",
        (datetime.now(UTC), fact_id),
    )
    await db.commit()


async def get_relevant_facts(
    db: aiosqlite.Connection,
    user_id: int,
    query: str,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    limit = limit or CONFIG.max_facts_per_query
    all_facts = await get_facts(db, user_id)
    if not all_facts:
        return []

    import jieba

    query_tokens = set(jieba.lcut(query))

    scored: list[tuple[int, dict[str, Any]]] = []
    for f in all_facts:
        fact_tokens = set(jieba.lcut(f["fact"]))
        overlap = len(query_tokens & fact_tokens)
        if overlap > 0:
            scored.append((overlap, f))

    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [f for _, f in scored[:limit]]

    for f in selected:
        await _touch_fact(db, f["id"])
    return selected
