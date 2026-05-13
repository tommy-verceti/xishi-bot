"""Tests for v2-engine filter module — message noise filtering.

Covers: blocking keywords, clean patterns, pass-through, edge cases.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "v2-engine"))

from filter import filter_send_msg


class TestBlockKeywords:
    def test_block_queue_notice(self):
        msg = {
            "action": "send_msg",
            "params": {
                "message": [
                    {"type": "text", "data": {"text": "任务完成后处理 请稍等"}}
                ]
            },
        }
        result = filter_send_msg(msg)
        assert result.action == "block"
        assert result.data is None

    def test_block_keyword_in_string_message(self):
        msg = {
            "action": "send_msg",
            "params": {"message": "你好 任务完成后处理 再见"},
        }
        result = filter_send_msg(msg)
        assert result.action == "block"

    def test_normal_message_passes(self):
        msg = {
            "action": "send_msg",
            "params": {
                "message": [
                    {"type": "text", "data": {"text": "你好呀~"}}
                ]
            },
        }
        result = filter_send_msg(msg)
        assert result.action == "modify"


class TestCleanPatterns:
    def test_clean_context_indicator(self):
        msg = {
            "action": "send_msg",
            "params": {
                "message": [
                    {"type": "text", "data": {"text": "回复内容 [ctx:25%] 上下文"}}
                ]
            },
        }
        result = filter_send_msg(msg)
        cleaned = result.data["params"]["message"][0]["data"]["text"]
        assert "回复内容" in cleaned
        assert "[ctx:" not in cleaned

    def test_clean_workdir_patterns(self):
        for pattern in ["~/gf-bot", "~/my-agent"]:
            msg = {
                "action": "send_msg",
                "params": {
                    "message": [
                        {
                            "type": "text",
                            "data": {"text": f"消息 {pattern} 路径"},
                        }
                    ]
                },
            }
            result = filter_send_msg(msg)
            text = result.data["params"]["message"][0]["data"]["text"]
            assert pattern not in text

    def test_clean_thinking_emoji(self):
        msg = {
            "action": "send_msg",
            "params": {
                "message": [
                    {
                        "type": "text",
                        "data": {
                            "text": "正常回复 \U0001f4ad 思考过程... 更多"
                        },
                    }
                ]
            },
        }
        result = filter_send_msg(msg)
        text = result.data["params"]["message"][0]["data"]["text"]
        assert "正常回复" in text
        assert "思考过程" not in text


class TestPassThrough:
    def test_non_send_msg_passes(self):
        msg = {"action": "get_status", "params": {}}
        result = filter_send_msg(msg)
        assert result.action == "pass"

    def test_empty_after_clean_is_blocked(self):
        msg = {
            "action": "send_msg",
            "params": {
                "message": [
                    {"type": "text", "data": {"text": "\U0001f4ad only thinking"}}
                ]
            },
        }
        result = filter_send_msg(msg)
        assert result.action == "block"


class TestArraySegments:
    def test_preserves_non_text_segments(self):
        msg = {
            "action": "send_msg",
            "params": {
                "message": [
                    {"type": "image", "data": {"file": "pic.png"}},
                    {"type": "text", "data": {"text": "你好[ctx:10%]"}},
                ]
            },
        }
        result = filter_send_msg(msg)
        segments = result.data["params"]["message"]
        assert len(segments) == 2
        assert segments[0]["type"] == "image"

    def test_blocked_segment_removed_others_preserved(self):
        msg = {
            "action": "send_msg",
            "params": {
                "message": [
                    {"type": "text", "data": {"text": "任务完成后处理"}},
                    {"type": "image", "data": {"file": "emoji.png"}},
                ]
            },
        }
        result = filter_send_msg(msg)
        segments = result.data["params"]["message"]
        assert len(segments) == 1
        assert segments[0]["type"] == "image"
