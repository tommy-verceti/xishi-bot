"""Emotion engine — favorability scoring and mood state machine.

Phase 2 core. Favorability: -1.0 to 1.0 (hidden).
Mood: discrete states expressed through Xishi's language.
"""

import logging
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from config import CONFIG

logger = logging.getLogger(__name__)

POSITIVE_KEYWORDS: tuple[str, ...] = (
    "喜欢", "谢谢", "开心", "哈哈", "好棒", "可爱",
    "有眼光", "想你", "抱抱", "厉害", "早", "晚安", "早安",
    "嘿嘿", "嘿嘿", "啦",
)
NEGATIVE_KEYWORDS: tuple[str, ...] = (
    "烦", "累", "难过", "不开心", "滚", "无聊",
    "别烦我", "别说了", "关掉", "不理你了",
)


async def get_or_create_emotion(
    db: aiosqlite.Connection, user_id: int
) -> dict[str, Any]:
    rows = await db.execute_fetchall(
        "SELECT * FROM emotions WHERE user_id = ?", (user_id,)
    )
    if rows:
        return dict(rows[0])
    await db.execute(
        "INSERT INTO emotions (user_id, total_interactions) VALUES (?, 0)",
        (user_id,),
    )
    await db.commit()
    rows = await db.execute_fetchall(
        "SELECT * FROM emotions WHERE user_id = ?", (user_id,)
    )
    return dict(rows[0])


def _count_signals(text: str) -> tuple[int, int]:
    pos = sum(1 for kw in POSITIVE_KEYWORDS if kw in text)
    neg = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text)
    return pos, neg


def _compute_mood(favorability: float, hour: int, signals: tuple[int, int]) -> str:
    pos, neg = signals
    if neg > pos * 2:
        return "annoyed"
    if hour < 7 or hour >= 23:
        return "sleepy"
    if pos > neg and favorability > 0.3:
        return "happy"
    if pos > neg:
        return "playful"
    if favorability < -0.2:
        return "annoyed"
    if favorability < 0.1:
        return "shy"
    return "calm"


async def update_on_user_message(
    db: aiosqlite.Connection, user_id: int, text: str
) -> dict[str, Any]:
    em = await get_or_create_emotion(db, user_id)
    pos, neg = _count_signals(text)
    now = datetime.now(timezone.utc)
    hour = datetime.now().hour

    favorability = float(em["favorability"]) + 0.005
    favorability += pos * 0.02
    favorability -= neg * 0.03
    favorability = max(-1.0, min(1.0, favorability))

    new_mood = _compute_mood(favorability, hour, (pos, neg))

    await db.execute(
        "UPDATE emotions SET favorability = ?, current_mood = ?, "
        "mood_updated_at = ?, total_interactions = total_interactions + 1, "
        "positive_signals = positive_signals + ?, "
        "negative_signals = negative_signals + ?, "
        "last_mood_transition = ? WHERE user_id = ?",
        (
            favorability, new_mood, now, pos, neg,
            (f"{em['current_mood']} -> {new_mood}"
             if em["current_mood"] != new_mood else None),
            user_id,
        ),
    )
    await db.commit()
    logger.debug("Emotion: user %s favor=%.3f mood=%s", user_id, favorability, new_mood)
    return {"favorability": favorability, "current_mood": new_mood,
            "mood_intensity": em.get("mood_intensity", 0.5)}


async def update_on_reply(
    db: aiosqlite.Connection, user_id: int, reply_text: str
) -> None:
    em = await get_or_create_emotion(db, user_id)
    now = datetime.now(timezone.utc)
    length_bonus = min(0.01, len(reply_text) * 0.0001)
    favorability = float(em["favorability"]) + length_bonus
    favorability = max(-1.0, min(1.0, favorability))
    await db.execute(
        "UPDATE emotions SET favorability = ?, mood_updated_at = ? WHERE user_id = ?",
        (favorability, now, user_id),
    )
    await db.commit()


async def apply_decay(db: aiosqlite.Connection) -> None:
    rows = await db.execute_fetchall(
        "SELECT e.id, e.user_id, e.favorability, e.mood_updated_at, u.last_seen "
        "FROM emotions e JOIN users u ON e.user_id = u.id"
    )
    now = datetime.now(timezone.utc)
    for row in rows:
        last = row["last_seen"] or row["mood_updated_at"]
        if last is None:
            continue
        last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
        days = (now - last_dt).days
        if days >= CONFIG.favorability_decay_days:
            new_fav = float(row["favorability"]) - CONFIG.favorability_decay_rate
            new_fav = max(-1.0, new_fav)
            await db.execute(
                "UPDATE emotions SET favorability = ? WHERE id = ?",
                (new_fav, row["id"]),
            )
    await db.commit()
