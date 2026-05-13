"""Sticker matcher — keyword + emotion heuristic.

Phase 3: Matches Xishi's reply text against sticker library.
No LLM call — pure jieba tokenization + tag overlap + emotion boost.
"""

import json
import logging
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)

MATCH_THRESHOLD: float = 0.6
EMOTION_BONUS: float = 0.15


async def match_sticker(
    db: aiosqlite.Connection, reply_text: str, current_mood: str
) -> dict[str, Any] | None:
    """Find the best matching sticker for a reply, or None."""
    import jieba

    rows = await db.execute_fetchall("SELECT * FROM stickers")
    all_stickers = [dict(r) for r in rows]
    if not all_stickers:
        return None

    reply_tokens = set(jieba.lcut(reply_text))

    best_score: float = 0.0
    best_sticker: dict[str, Any] | None = None

    for sticker in all_stickers:
        tags_raw = sticker.get("tags", "[]")
        try:
            tags = json.loads(tags_raw) if isinstance(tags_raw, str) else tags_raw
        except (json.JSONDecodeError, TypeError):
            tags = []

        tag_tokens: set[str] = set()
        for t in tags:
            tag_tokens.update(jieba.lcut(t))

        if not tag_tokens:
            continue

        intersection = len(reply_tokens & tag_tokens)
        union = len(reply_tokens | tag_tokens)
        overlap_score = intersection / union if union > 0 else 0.0
        emotion_bonus = EMOTION_BONUS if sticker.get("emotion_match") == current_mood else 0.0
        total_score = overlap_score + emotion_bonus

        if total_score > best_score:
            best_score = total_score
            best_sticker = sticker

    if best_score >= MATCH_THRESHOLD and best_sticker:
        await db.execute(
            "UPDATE stickers SET usage_count = usage_count + 1 WHERE id = ?",
            (best_sticker["id"],),
        )
        await db.commit()
        logger.debug("Matched sticker: %s (score=%.2f)", best_sticker["name"], best_score)
        return best_sticker

    return None


def build_sticker_segment(sticker: dict[str, Any]) -> dict[str, Any]:
    return {"type": "image", "data": {"file": sticker["file_path"]}}
