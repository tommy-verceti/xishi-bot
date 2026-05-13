"""Send QQ notification to 小杰 via NapCat WebSocket."""
import asyncio
import json
import websockets

TARGET = "3066862564"
MSG = (
    "小杰~ V2版本说明书已经生成好啦！\n"
    "文件在桌面上：西施Bot-V2版本说明书.pdf\n"
    "V2 Engine所有代码也写完了，包括记忆、情绪、"
    "主动消息、表情包和Web面板~"
)


async def main() -> None:
    try:
        async with websockets.connect("ws://127.0.0.1:3001") as ws:
            echo_id = "notify_v2_complete"
            payload = json.dumps({
                "action": "send_private_msg",
                "params": {
                    "user_id": TARGET,
                    "message": [{"type": "text", "data": {"text": MSG}}],
                },
                "echo": echo_id,
            }, ensure_ascii=False)
            await ws.send(payload)
            # Wait for the actual API response, skipping events
            for _ in range(10):
                resp = await asyncio.wait_for(ws.recv(), timeout=5)
                result = json.loads(resp)
                if result.get("echo") == echo_id:
                    if result.get("status") == "ok":
                        print(f"Sent to {TARGET}")
                    else:
                        print(f"Failed: {result}")
                    return
            print("No matching response received")
    except Exception as e:
        print(f"Error: {e}")
        print("Ensure NapCat is running with WS at :3001")


asyncio.run(main())
