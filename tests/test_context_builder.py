"""Tests for context/builder.py — memory context block construction."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "v2-engine"))

from context.builder import build_context, inject_context


class TestBuildContext:
    def test_user_with_preferred_name(self):
        user = {"qq_id": "123", "preferred_name": "小杰", "nickname": "杰哥"}
        result = build_context(user=user)
        assert "用户: 小杰" in result
        assert "称呼: 小杰" in result

    def test_user_fallback_to_nickname(self):
        user = {"qq_id": "123", "nickname": "杰哥"}
        result = build_context(user=user)
        assert "用户: 杰哥" in result

    def test_user_fallback_to_qq(self):
        user = {"qq_id": "654321"}
        result = build_context(user=user)
        assert "QQ654321" in result

    def test_facts_listed(self):
        user = {"qq_id": "1", "preferred_name": "小明"}
        facts = [{"fact": "喜欢红烧肉"}, {"fact": "大学生"}]
        result = build_context(user=user, facts=facts)
        assert "喜欢红烧肉" in result
        assert "大学生" in result

    def test_empty_facts_no_section(self):
        result = build_context(user={"qq_id": "1"}, facts=[])
        assert "[Ta告诉过你]" not in result

    def test_emotion_happy_forward(self):
        result = build_context(
            user={"qq_id": "1"},
            emotion={"current_mood": "happy", "favorability": 0.5},
        )
        assert "心情: happy" in result
        assert "好感度: 正向" in result

    def test_favorability_label_neutral(self):
        result = build_context(
            user={"qq_id": "1"},
            emotion={"favorability": 0.1},
        )
        assert "中性" in result

    def test_favorability_label_needs_care(self):
        result = build_context(
            user={"qq_id": "1"},
            emotion={"favorability": -0.3},
        )
        assert "需要关心" in result

    def test_insights_section(self):
        result = build_context(
            user={"qq_id": "1"},
            insights=[{"insight": "兴趣: 游戏"}, {"insight": "性格: 活泼"}],
        )
        assert "[你感觉Ta]" in result
        assert "游戏" in result

    def test_summaries_section(self):
        result = build_context(
            user={"qq_id": "1"},
            summaries=[{"summary": "昨天聊了新皮肤"}],
        )
        assert "[最近聊过]" in result
        assert "新皮肤" in result

    def test_all_layers_combined(self):
        result = build_context(
            user={"qq_id": "1", "preferred_name": "小杰"},
            facts=[{"fact": "喜欢猫"}],
            emotion={"current_mood": "playful", "favorability": 0.6},
            insights=[{"insight": "游戏爱好者"}],
            summaries=[{"summary": "上周聊了考试"}],
        )
        assert "[系统记忆]" in result
        assert "小杰" in result
        assert "playful" in result
        assert "喜欢猫" in result
        assert "游戏爱好者" in result
        assert "考试" in result

    def test_none_user_handled(self):
        result = build_context(user=None)
        assert "[系统记忆]" in result
        assert "---" in result


class TestInjectContext:
    def test_context_before_message(self):
        original = "西施你好呀~"
        context = "[系统记忆]\n用户: 小杰\n---"
        result = inject_context(original, context)
        assert result.startswith("[系统记忆]")
        assert original in result
        assert result.index(context) < result.index(original)
