import asyncio
import json
import websockets

UPSTREAM = "ws://127.0.0.1:3001"
LISTEN = ("127.0.0.1", 3002)

BLOCK_KEYWORDS = [
    "任务完成后处理",  # "任务完成后处理"
]

CLEAN_PATTERNS = [
    "[ctx:",
    "~/gf-bot",
    "~/my-agent",
]

THINKING_PREFIX = "\U0001f4ad"


def clean_text(text: str) -> str:
    for p in CLEAN_PATTERNS:
        idx = text.find(p)
        if idx != -1:
            text = text[:idx].rstrip()
    if THINKING_PREFIX in text:
        idx = text.find(THINKING_PREFIX)
        text = text[:idx].rstrip()
    return text.strip()


def text_from_message(message) -> str:
    if isinstance(message, str):
        return message
    if isinstance(message, list):
        parts = []
        for seg in message:
            if seg.get("type") == "text":
                parts.append(seg.get("data", {}).get("text", ""))
        return "".join(parts)
    return ""


def filter_send_msg(data: dict) -> dict | None:
    if data.get("action") != "send_msg":
        return data

    params = data.get("params", {})
    message = params.get("message", [])
    full_text = text_from_message(message)

    # 调试：写所有 send_msg 到日志文件
    with open("E:/xishi-bot/qq-proxy/proxy.log", "a", encoding="utf-8") as f:
        f.write(f"[SEND] {full_text[:150]}\n")

    for kw in BLOCK_KEYWORDS:
        if kw in full_text:
            print(f"[BLOCKED] {full_text[:80]}")
            with open("E:/xishi-bot/qq-proxy/proxy.log", "a", encoding="utf-8") as f:
                f.write(f"[BLOCKED] {full_text[:150]}\n")
            return None

    if isinstance(message, str):
        cleaned = clean_text(message)
        if not cleaned:
            return None
        data["params"]["message"] = cleaned
        return data

    if isinstance(message, list):
        new_segments = []
        for seg in message:
            if seg.get("type") != "text":
                new_segments.append(seg)
                continue
            text = seg.get("data", {}).get("text", "")
            if any(kw in text for kw in BLOCK_KEYWORDS):
                print(f"[BLOCKED-seg] {text[:80]}")
                with open("E:/xishi-bot/qq-proxy/proxy.log", "a", encoding="utf-8") as f:
                    f.write(f"[BLOCKED-seg] {text[:150]}\n")
                continue
            cleaned = clean_text(text)
            if not cleaned:
                continue
            seg["data"]["text"] = cleaned
            new_segments.append(seg)

        if not new_segments:
            return None
        data["params"]["message"] = new_segments
    return data


async def handle(websocket):
    try:
        async with websockets.connect(UPSTREAM) as upstream:
            async def up_to_down():
                async for msg in upstream:
                    await websocket.send(msg)

            async def down_to_up():
                async for msg in websocket:
                    try:
                        data = json.loads(msg)
                        filtered = filter_send_msg(data)
                        if filtered is not None:
                            await upstream.send(json.dumps(filtered))
                    except json.JSONDecodeError:
                        await upstream.send(msg)

            await asyncio.gather(up_to_down(), down_to_up())
    except Exception:
        pass


async def main():
    async with websockets.serve(handle, *LISTEN):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
