"""Message filtering logic ported from V1 proxy.py.

Blocks noise (queue notices, thinking output, context indicators)
from cc-connect outbound messages before delivery to QQ.
"""

import logging
from dataclasses import dataclass
from typing import Any

from config import CONFIG

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FilterResult:
    action: str  # "pass", "block", "modify"
    data: dict[str, Any] | None


def _clean_text(text: str) -> str:
    for pattern in CONFIG.clean_patterns:
        idx = text.find(pattern)
        if idx != -1:
            text = text[:idx].rstrip()
    if CONFIG.thinking_prefix in text:
        idx = text.find(CONFIG.thinking_prefix)
        text = text[:idx].rstrip()
    return text.strip()


def _text_from_message(message: object) -> str:
    if isinstance(message, str):
        return message
    if isinstance(message, list):
        parts: list[str] = []
        for seg in message:
            if isinstance(seg, dict) and seg.get("type") == "text":
                parts.append(seg.get("data", {}).get("text", ""))
        return "".join(parts)
    return ""


def filter_send_msg(data: dict[str, Any]) -> FilterResult:
    if data.get("action") != "send_msg":
        return FilterResult(action="pass", data=data)

    params = data.get("params", {})
    message = params.get("message", [])
    full_text = _text_from_message(message)

    logger.debug("Outbound: %s", full_text[:120])

    for kw in CONFIG.block_keywords:
        if kw in full_text:
            logger.info("Blocked: %s", full_text[:80])
            # For string messages, block entirely.
            # For array messages, let per-segment filtering handle it
            # (preserves non-text segments like images).
            if isinstance(message, str):
                return FilterResult(action="block", data=None)
            # Fall through to segment-level processing

    if isinstance(message, str):
        cleaned = _clean_text(message)
        if not cleaned:
            return FilterResult(action="block", data=None)
        data["params"]["message"] = cleaned
        return FilterResult(action="modify", data=data)

    if isinstance(message, list):
        new_segments: list[dict[str, Any]] = []
        for seg in message:
            if seg.get("type") != "text":
                new_segments.append(seg)
                continue
            text = seg.get("data", {}).get("text", "")
            if any(kw in text for kw in CONFIG.block_keywords):
                logger.info("Blocked segment: %s", text[:80])
                continue
            cleaned = _clean_text(text)
            if not cleaned:
                continue
            seg["data"]["text"] = cleaned
            new_segments.append(seg)

        if not new_segments:
            return FilterResult(action="block", data=None)
        data["params"]["message"] = new_segments
        return FilterResult(action="modify", data=data)

    return FilterResult(action="pass", data=data)
