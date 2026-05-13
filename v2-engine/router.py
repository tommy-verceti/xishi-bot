"""WebSocket message router — central interception loop.

Phase 0: Bidirectional relay with outbound filtering.
Phase 1: Memory context injection on inbound, dev command interception.
Phase 2: Emotion updates on inbound/outbound.
Phase 3: Sticker matching on outbound.
"""

import asyncio
import json
import logging

import websockets

from config import CONFIG
from db.database import get_db
from filter import filter_send_msg

logger = logging.getLogger(__name__)


def _extract_text(message: object) -> str:
    if isinstance(message, str):
        return message
    if isinstance(message, list):
        parts: list[str] = []
        for seg in message:
            if isinstance(seg, dict) and seg.get("type") == "text":
                parts.append(seg.get("data", {}).get("text", ""))
        return "".join(parts)
    return ""


def _build_direct_reply(orig_data: dict, reply_text: str) -> str:
    user_id = orig_data.get("user_id") or orig_data.get("sender", {}).get("user_id", "")
    return json.dumps({
        "action": "send_private_msg",
        "params": {
            "user_id": user_id,
            "message": [{"type": "text", "data": {"text": reply_text}}],
        },
    }, ensure_ascii=False)


def _is_private_message(data: dict) -> bool:
    post_type = data.get("post_type", "")
    if post_type == "message":
        return data.get("message_type") == "private"
    return data.get("type") == "message" and data.get("sub_type") == "private"


async def handle(websocket: websockets.WebSocketServerProtocol) -> None:
    peer = f"{websocket.remote_address}"
    logger.info("cc-connect connected: %s", peer)

    db = await get_db()
    # Track current user for outbound context
    current_user: dict | None = None

    try:
        async with websockets.connect(CONFIG.napcat_ws_url) as upstream:
            logger.info("Connected to NapCat at %s", CONFIG.napcat_ws_url)

            async def up_to_down() -> None:
                """NapCat -> cc-connect: memory + emotion + dev commands."""
                nonlocal current_user
                from memory.manager import process_inbound
                from emotion.engine import update_on_user_message

                async for msg in upstream:
                    try:
                        data = json.loads(msg)
                    except json.JSONDecodeError:
                        await websocket.send(msg)
                        continue

                    if not _is_private_message(data):
                        await websocket.send(msg)
                        continue

                    user_id = str(
                        data.get("user_id") or data.get("sender", {}).get("user_id", "")
                    )
                    raw_text = _extract_text(
                        data.get("message") or data.get("raw_message", "")
                    )

                    if not user_id or not raw_text:
                        await websocket.send(msg)
                        continue

                    # Phase 1: Memory pipeline
                    enriched_text, user, cmd_result = await process_inbound(
                        db, user_id, raw_text, msg
                    )
                    current_user = user

                    # Dev command interception
                    if cmd_result and cmd_result.get("action") == "reply_direct":
                        reply = _build_direct_reply(data, cmd_result["message"])
                        await upstream.send(reply)
                        continue

                    # Phase 2: Update emotion from user message
                    await update_on_user_message(db, user["id"], raw_text)

                    # Inject enriched text
                    if data.get("message_type") == "private":
                        data["raw_message"] = enriched_text
                        data["message"] = [
                            {"type": "text", "data": {"text": enriched_text}}
                        ]

                    await websocket.send(json.dumps(data, ensure_ascii=False))

            async def down_to_up() -> None:
                """cc-connect -> NapCat: filter + emotion + stickers + store."""
                from emotion.engine import update_on_reply
                from stickers.matcher import match_sticker, build_sticker_segment
                from memory.manager import process_outbound

                nonlocal current_user

                async for msg in websocket:
                    try:
                        data = json.loads(msg)
                    except json.JSONDecodeError:
                        await upstream.send(msg)
                        continue

                    result = filter_send_msg(data)
                    if result.action == "block":
                        continue

                    out_data = result.data or data

                    # Phase 3: Sticker matching
                    if out_data.get("action") == "send_msg" and current_user:
                        out_text = _extract_text(out_data.get("params", {}).get("message", ""))
                        if out_text:
                            # Phase 2: Update emotion from Xishi's reply
                            await update_on_reply(db, current_user["id"], out_text)

                            # Phase 3: Match and attach sticker
                            from emotion.engine import get_or_create_emotion
                            em = await get_or_create_emotion(db, current_user["id"])
                            sticker = await match_sticker(
                                db, out_text, em.get("current_mood", "calm")
                            )
                            if sticker:
                                msg_arr = out_data["params"].get("message", [])
                                if isinstance(msg_arr, list):
                                    msg_arr.insert(0, build_sticker_segment(sticker))
                                    out_data["params"]["message"] = msg_arr
                                    logger.debug("Attached sticker: %s", sticker["name"])

                            # Phase 1: Store outbound
                            await process_outbound(
                                db, current_user, out_text, msg,
                                has_sticker=1 if sticker else 0,
                                sticker_id=sticker["id"] if sticker else None,
                            )

                    await upstream.send(json.dumps(out_data, ensure_ascii=False))

            await asyncio.gather(up_to_down(), down_to_up())

    except websockets.exceptions.ConnectionClosed:
        logger.info("Connection closed: %s", peer)
    except Exception:
        logger.exception("Error in handler for %s", peer)
    finally:
        await db.close()


async def main() -> None:
    logger.info(
        "V2 Engine WS relay starting on %s:%s -> upstream %s",
        CONFIG.listen_host, CONFIG.listen_port, CONFIG.napcat_ws_url,
    )
    async with websockets.serve(handle, CONFIG.listen_host, CONFIG.listen_port):
        await asyncio.Future()
