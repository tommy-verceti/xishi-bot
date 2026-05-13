"""Proactive message scheduler.

Phase 4: Timed, random, and reminder proactive messages.
"""

import asyncio
import logging
import random
from datetime import UTC, datetime, timedelta
from typing import Any

import aiosqlite
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from config import CONFIG
from db.database import get_db
from db.queries import get_active_users

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _count_today_proactive(db: aiosqlite.Connection, user_id: int) -> int:
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    rows = await db.execute_fetchall(
        "SELECT COUNT(*) as cnt FROM task_log "
        "WHERE user_id = ? AND fired_at >= ? AND status = 'sent'",
        (user_id, today),
    )
    return rows[0]["cnt"] if rows else 0


async def _generate_proactive_message(
    user: dict[str, Any], em: dict[str, Any] | None, msg_type: str
) -> str:
    from openai import AsyncOpenAI

    mood = em.get("current_mood", "calm") if em else "calm"
    name = (
        user.get("preferred_name")
        or user.get("nickname")
        or f"QQ{user['qq_id']}"
    )

    system_prompt = (
        "你是施夷光（西施），17岁，稷下学院学生。活泼机灵、市井少女。"
        "说话短句跳跃，尾音带~，多用语气词。你现在主动给朋友发QQ消息。"
        "生成2-3句自然消息。"
    )

    prompts = {
        "morning": f"给{name}发早安消息。刚醒还有点迷糊。语气可爱俏皮。",
        "night": f"给{name}发晚安消息。准备睡了。语气温柔安静。",
        "random": f"给{name}发随机搭话。心情{mood}。分享小事或问对方在干嘛。语气随意自然。",
        "reminder": f"给{name}发消息。很久没见了，有点想他。语气带小抱怨但可爱。问最近在干嘛。",
    }
    user_prompt = prompts.get(msg_type, prompts["random"])

    try:
        client = AsyncOpenAI(
            api_key=CONFIG.deepseek_api_key,
            base_url=CONFIG.deepseek_base_url,
        )
        resp = await client.chat.completions.create(
            model=CONFIG.deepseek_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=120,
            temperature=0.9,
        )
        text = resp.choices[0].message.content or "..."
        return text.strip().strip('"')
    except Exception:
        logger.exception("Proactive gen failed")
        fallbacks = {
            "morning": "早呀~ 今天的阳光不错呢！",
            "night": "晚安啦~ 明天见哦！",
            "random": "嘿~ 你在干嘛呀？",
            "reminder": "好久不见啦...你是不是忘了我了？",
        }
        return fallbacks.get(msg_type, "嘿~ 想你了就来找你啦！")


async def _send_one(
    db: aiosqlite.Connection, user: dict[str, Any], msg_type: str
) -> None:
    user_id = user["qq_id"]
    count = await _count_today_proactive(db, user["id"])
    if count >= CONFIG.proactive_max_per_user_day:
        return

    rows = await db.execute_fetchall(
        "SELECT * FROM emotions WHERE user_id = ?", (user["id"],)
    )
    em = dict(rows[0]) if rows else None

    text = await _generate_proactive_message(user, em, msg_type)

    from napcat.client import send_private_msg

    result = await send_private_msg(user_id, text)
    status = "sent" if result else "failed"
    await db.execute(
        "INSERT INTO task_log (user_id, message_sent, fired_at, status) "
        "VALUES (?, ?, ?, ?)",
        (user["id"], text, datetime.now(UTC), status),
    )
    await db.commit()
    logger.info("Proactive %s -> %s: %s", msg_type, user_id, text[:60])


async def _morning() -> None:
    db = await get_db()
    try:
        users = await get_active_users(db)
        for u in random.sample(users, min(3, len(users))):
            await _send_one(db, u, "morning")
            await asyncio.sleep(5)
    finally:
        await db.close()


async def _night() -> None:
    db = await get_db()
    try:
        users = await get_active_users(db)
        for u in random.sample(users, min(2, len(users))):
            await _send_one(db, u, "night")
            await asyncio.sleep(5)
    finally:
        await db.close()


async def _random_checkin() -> None:
    db = await get_db()
    try:
        users = await get_active_users(db)
        if users:
            await _send_one(db, random.choice(users), "random")
    finally:
        await db.close()


async def _reminder() -> None:
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            "SELECT u.* FROM users u "
            "WHERE u.is_active = 1 "
            "AND (u.last_seen < ? OR u.last_seen IS NULL) "
            "GROUP BY u.id",
            (datetime.now(UTC) - timedelta(hours=72),),
        )
        for u_dict in [dict(r) for r in rows][:2]:
            await _send_one(db, u_dict, "reminder")
            await asyncio.sleep(5)
    finally:
        await db.close()


async def _decay() -> None:
    from emotion.engine import apply_decay
    db = await get_db()
    try:
        await apply_decay(db)
    finally:
        await db.close()


def start_scheduler() -> None:
    scheduler.add_job(_morning, CronTrigger(hour=8, minute=15), id="morning")
    scheduler.add_job(_night, CronTrigger(hour=22, minute=30), id="night")
    scheduler.add_job(_random_checkin, CronTrigger(hour="9-21/4", minute=45), id="random")
    scheduler.add_job(_reminder, CronTrigger(hour=12, minute=0), id="reminder")
    scheduler.add_job(_decay, CronTrigger(hour=3, minute=0), id="decay")
    scheduler.start()
    logger.info("Scheduler started: 5 jobs")
