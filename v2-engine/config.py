"""V2 Engine configuration. All values read from environment with sensible defaults."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    # WebSocket
    napcat_ws_url: str = "ws://127.0.0.1:3001"
    listen_host: str = "127.0.0.1"
    listen_port: int = 3002

    # NapCat HTTP (for proactive messages)
    napcat_http_url: str = "http://127.0.0.1:4000"

    # Database
    db_path: str = "E:/xishi-bot/v2-engine/data/xishi.db"

    # Deepseek API (Xishi's model)
    deepseek_api_key: str = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
    deepseek_base_url: str = os.environ.get(
        "ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic"
    )
    deepseek_model: str = os.environ.get(
        "ANTHROPIC_MODEL", "deepseek-v4-pro[1m]"
    )

    # Dev panel
    web_host: str = "127.0.0.1"
    web_port: int = 8080
    web_password: str = ""

    # Memory
    max_context_tokens: int = 300
    max_facts_per_query: int = 5
    max_summaries_per_query: int = 2
    summary_trigger_messages: int = 50
    insight_trigger_messages: int = 20

    # Emotion
    favorability_decay_days: int = 7
    favorability_decay_rate: float = 0.02

    # Proactive messages
    proactive_max_per_user_day: int = 2

    # Filtering (ported from V1 proxy.py)
    block_keywords: tuple[str, ...] = ("任务完成后处理",)
    clean_patterns: tuple[str, ...] = ("[ctx:", "~/gf-bot", "~/my-agent")
    thinking_prefix: str = "\U0001f4ad"

    # Logging
    log_dir: str = "E:/xishi-bot/v2-engine/logs"
    log_level: str = "INFO"

    # Claude idle reset
    session_idle_threshold_hours: int = 2


CONFIG = Config()
