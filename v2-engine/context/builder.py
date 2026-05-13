"""Builds memory context block injected before user messages.

Phase 1: L1 (user identity) + L2 (facts).
Phase 2: Adds emotion.
Phase 5: Adds L3 (insights) + L4 (summaries).
"""

from typing import Any


def _favorability_label(score: float) -> str:
    if score >= 0.4:
        return "正向"
    if score >= 0.0:
        return "中性"
    return "需要关心"


def build_context(
    user: dict[str, Any] | None = None,
    facts: list[dict[str, Any]] | None = None,
    emotion: dict[str, Any] | None = None,
    insights: list[dict[str, Any]] | None = None,
    summaries: list[dict[str, Any]] | None = None,
) -> str:
    parts: list[str] = ["[系统记忆]"]

    # L1: User identity
    if user:
        name = (
            user.get("preferred_name")
            or user.get("nickname")
            or f"QQ{user['qq_id']}"
        )
        parts.append(f"用户: {name}")
        if user.get("preferred_name"):
            parts[-1] += f" | 称呼: {user['preferred_name']}"

    # L5: Emotion (Phase 2+)
    if emotion:
        mood = emotion.get("current_mood", "calm")
        label = _favorability_label(emotion.get("favorability", 0.1))
        parts.append(f"心情: {mood} | 好感度: {label}")

    # L2: Facts
    if facts:
        fact_strs = [f["fact"] for f in facts]
        parts.append(f"[Ta告诉过你]: {'; '.join(fact_strs)}")

    # L3: Insights (Phase 5+)
    if insights:
        insight_strs = [i["insight"] for i in insights]
        parts.append(f"[你感觉Ta]: {'; '.join(insight_strs)}")

    # L4: Summaries (Phase 5+)
    if summaries:
        summary_strs = [s["summary"] for s in summaries]
        parts.append(f"[最近聊过]: {' '.join(summary_strs)}")

    parts.append("---")
    return "\n".join(parts)


def inject_context(original_message: str, context: str) -> str:
    return f"{context}\n{original_message}"
