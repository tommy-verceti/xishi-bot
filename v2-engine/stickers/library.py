"""Sticker library — metadata and seeding.

Phase 3: Index sticker files with tags and emotion matches.
"""

import json
import logging
import os
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)

DEFAULT_STICKERS: list[dict[str, Any]] = [
    {"name": "xishi_waving", "file": "xishi_waving.png",
     "tags": ["早安", "挥手", "打招呼", "你好", "嗨"], "emotion": "happy"},
    {"name": "xishi_smile", "file": "xishi_smile.png",
     "tags": ["开心", "笑", "哈哈", "有眼光", "嘿嘿"], "emotion": "happy"},
    {"name": "xishi_shy", "file": "xishi_shy.png",
     "tags": ["害羞", "不好意思", "谢谢", "夸"], "emotion": "shy"},
    {"name": "xishi_angry", "file": "xishi_angry.png",
     "tags": ["笨蛋", "生气", "来抓我呀", "讨厌"], "emotion": "annoyed"},
    {"name": "xishi_think", "file": "xishi_think.png",
     "tags": ["嗯", "想", "思考", "让我想想"], "emotion": "thoughtful"},
    {"name": "xishi_sleepy", "file": "xishi_sleepy.png",
     "tags": ["困", "晚安", "睡了", "累"], "emotion": "sleepy"},
    {"name": "xishi_playful", "file": "xishi_playful.png",
     "tags": ["来玩", "追我", "嘻嘻", "嘿嘿", "~"], "emotion": "playful"},
    {"name": "xishi_calm", "file": "xishi_calm.png",
     "tags": ["嗯", "好", "知道了", "可以"], "emotion": "calm"},
    {"name": "xishi_treasure", "file": "xishi_treasure.png",
     "tags": ["珍宝", "宝藏", "眼光", "宝物", "有价值的"], "emotion": "happy"},
    {"name": "xishi_gentle", "file": "xishi_gentle.png",
     "tags": ["温柔", "没关系", "陪伴", "加油"], "emotion": "calm"},
]

# Minimal valid 1x1 pink PNG placeholder
_PLACEHOLDER_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


async def seed_stickers(db: aiosqlite.Connection, files_dir: str) -> None:
    rows = await db.execute_fetchall("SELECT COUNT(*) as cnt FROM stickers")
    if rows[0]["cnt"] > 0:
        logger.info("Stickers already seeded (%d)", rows[0]["cnt"])
        return

    os.makedirs(files_dir, exist_ok=True)

    for s in DEFAULT_STICKERS:
        file_path = os.path.join(files_dir, s["file"]).replace("\\", "/")
        await db.execute(
            "INSERT INTO stickers (name, file_path, tags, emotion_match) "
            "VALUES (?, ?, ?, ?)",
            (s["name"], f"file:///{file_path}",
             json.dumps(s["tags"], ensure_ascii=False), s["emotion"]),
        )

    await db.commit()
    logger.info("Seeded %d stickers", len(DEFAULT_STICKERS))

    for s in DEFAULT_STICKERS:
        placeholder = os.path.join(files_dir, s["file"])
        if not os.path.exists(placeholder):
            with open(placeholder, "wb") as f:
                f.write(_PLACEHOLDER_PNG)
    logger.info("Placeholder sticker files in %s", files_dir)
