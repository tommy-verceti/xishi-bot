"""Phase 0 smoke test for v2-engine."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import CONFIG
from filter import filter_send_msg

print("config OK")
print(f"  WS: {CONFIG.listen_host}:{CONFIG.listen_port} -> {CONFIG.napcat_ws_url}")
print(f"  DB: {CONFIG.db_path}")

# Test filters
block_msg = {
    "action": "send_msg",
    "params": {
        "message": [{"type": "text", "data": {"text": "Hi 任务完成后处理 bye"}}]
    },
}
result = filter_send_msg(block_msg)
assert result.action == "block", f"Expected block, got {result.action}"
print("Filter block test: PASS")

clean_msg = {
    "action": "send_msg",
    "params": {
        "message": [
            {
                "type": "text",
                "data": {"text": "Hello \U0001f4adthinking...\n[ctx:20%] footer"},
            }
        ]
    },
}
result2 = filter_send_msg(clean_msg)
assert result2.action == "modify"
text = result2.data["params"]["message"][0]["data"]["text"]
assert "thinking" not in text
assert "[ctx:" not in text
print(f"Filter clean test: PASS -> {text!r}")

# Test DB init
import asyncio

from db.database import get_db, init_db


async def test_db() -> None:
    db = await get_db(CONFIG.db_path)
    await init_db(db)
    tables = await db.execute_fetchall(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    for t in tables:
        print(f"  Table: {t['name']}")
    await db.close()
    os.remove(CONFIG.db_path)
    print("DB test: PASS (9 tables created)")


asyncio.run(test_db())

print("\nAll Phase 0 smoke tests passed!")
