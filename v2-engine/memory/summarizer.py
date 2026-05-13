"""Conversation summarizer and insight extractor.

Phase 5: L3 insight extraction + L4 conversation summaries via Deepseek API.
"""

import json
import logging
from typing import Any

from config import CONFIG

logger = logging.getLogger(__name__)


async def generate_summary(messages: list[dict[str, Any]]) -> str:
    if not messages:
        return ""

    dialogue = "\n".join(
        f"{'用户' if m['direction'] != 'outbound' else '西施'}: {m['content'][:200]}"
        for m in messages[-30:]
    )

    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=CONFIG.deepseek_api_key,
        base_url=CONFIG.deepseek_base_url,
    )
    try:
        resp = await client.chat.completions.create(
            model=CONFIG.deepseek_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是一个对话摘要助手。用2-3句中文总结以下对话的关键内容。"
                        "重点：用户说了什么重要的事、表达了什么情绪、提到了什么计划或事件。"
                        "只返回摘要文本，不要加前缀。"
                    ),
                },
                {"role": "user", "content": dialogue},
            ],
            max_tokens=200,
            temperature=0.5,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception:
        logger.exception("Summary generation failed")
        return ""


async def extract_insights(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not messages:
        return []

    dialogue = "\n".join(
        f"用户: {m['content'][:200]}"
        for m in messages[-20:]
        if m.get("direction") != "outbound"
    )
    if not dialogue.strip():
        return []

    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=CONFIG.deepseek_api_key,
        base_url=CONFIG.deepseek_base_url,
    )
    try:
        resp = await client.chat.completions.create(
            model=CONFIG.deepseek_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "根据对话内容，推断用户的兴趣、性格、习惯或生活状态。"
                        "返回JSON数组，每项有category(interest/personality/habit/life_event)"
                        "和insight字段。只返回JSON。无内容返回[]。"
                    ),
                },
                {"role": "user", "content": dialogue},
            ],
            max_tokens=300,
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        raw = (resp.choices[0].message.content or "[]").strip()
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            return parsed.get("insights", [])
        return []
    except Exception:
        logger.exception("Insight extraction failed")
        return []
