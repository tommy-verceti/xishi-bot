"""Memory manager — orchestrates memory operations per message.

Phase 1: L1 (user identity) + L2 (facts) + dev command interception.
Phase 2+: Emotion integration.
"""

import logging
from typing import Any

import aiosqlite

from context.builder import build_context, inject_context
from db.queries import (
    delete_facts,
    get_facts,
    get_or_create_user,
    get_relevant_facts,
    store_fact,
    store_message,
)

logger = logging.getLogger(__name__)


async def process_inbound(
    db: aiosqlite.Connection,
    qq_id: str,
    message_text: str,
    raw_payload: str,
) -> tuple[str, dict[str, Any], dict[str, Any] | None]:
    """Process an inbound message through the memory pipeline.

    Returns (enriched_message, user_record, command_result_or_None).
    """
    # L1: identify/create user
    user = await get_or_create_user(db, qq_id)

    # Intercept dev commands
    command_result = await _check_dev_command(db, user, message_text)
    if command_result:
        return message_text, user, command_result

    # L2: get relevant facts (jieba overlap scoring)
    facts = await get_relevant_facts(db, user["id"], message_text)

    # Build context block
    context = build_context(user=user, facts=facts)
    enriched = inject_context(message_text, context)

    # Store message
    await store_message(db, user["id"], "inbound", message_text, raw_payload=raw_payload)

    logger.debug("Injected context (%d facts) for user %s", len(facts), qq_id)
    return enriched, user, None


async def process_outbound(
    db: aiosqlite.Connection,
    user: dict[str, Any],
    message_text: str,
    raw_payload: str,
    has_sticker: int = 0,
    sticker_id: int | None = None,
) -> None:
    """Store an outbound message."""
    await store_message(
        db,
        user["id"],
        "outbound",
        message_text,
        raw_payload=raw_payload,
        has_sticker=has_sticker,
        sticker_id=sticker_id,
    )


# ── Dev command handlers ────────────────────────────────────


async def _check_dev_command(
    db: aiosqlite.Connection,
    user: dict[str, Any],
    text: str,
) -> dict[str, Any] | None:
    stripped = text.strip()

    if stripped.startswith("/记住 "):
        fact = stripped[4:].strip()
        if fact:
            await store_fact(db, user["id"], fact)
            return {
                "action": "reply_direct",
                "message": f"好的记住啦~ '{fact}'这件事我记下了！",
            }
        return {
            "action": "reply_direct",
            "message": "嗯？要记住什么呀？我没听清楚~",
        }

    if stripped.startswith("/忘记 "):
        keyword = stripped[4:].strip()
        if keyword:
            deleted = await delete_facts(db, user["id"], keyword)
            if deleted > 0:
                return {
                    "action": "reply_direct",
                    "message": f"嗯嗯，关于'{keyword}'的{deleted}条记忆已经忘掉了~",
                }
            return {
                "action": "reply_direct",
                "message": f"唔...我翻了翻记忆，好像没有关于'{keyword}'的事呢~",
            }
        return {
            "action": "reply_direct",
            "message": "忘记什么呀？说清楚一点嘛~",
        }

    if stripped == "/我是谁":
        facts = await get_facts(db, user["id"])
        if not facts:
            return {
                "action": "reply_direct",
                "message": (
                    "我还不太了解你呢...多跟我聊聊嘛！"
                    "或者用 /记住 告诉我你的事，我不会忘的~"
                ),
            }

        lines = ["嗯，让我想想关于你的事..."]
        for f in facts[:10]:
            lines.append(f"  • {f['fact']}")
        return {"action": "reply_direct", "message": "\n".join(lines)}

    return None
