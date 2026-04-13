"""
Single WebSocket per session.
Browser sends binary frames: 5-byte header (0xAA + uint32 LE sample rate) + float32 LE PCM.
Server responds with JSON subtitle payloads.
"""

import json

from fastapi import WebSocket, WebSocketDisconnect


async def ws_endpoint(websocket: WebSocket, process_audio_cb) -> None:
    await websocket.accept()
    chunk_n = 0
    try:
        while True:
            data = await websocket.receive()
            raw = data.get("bytes") or None
            if raw:
                chunk_n += 1
                # Log enough to debug protocol and size issues without flooding
                magic = raw[0] if raw else None
                print(f"[WS] chunk #{chunk_n} bytes={len(raw)} magic=0x{magic:02X}" if magic is not None else f"[WS] chunk #{chunk_n} bytes={len(raw)} empty")
                result = await process_audio_cb(raw)
                if result:
                    await websocket.send_text(
                        json.dumps(result, ensure_ascii=False)
                    )
            elif data.get("text"):
                print(f"[WS] text frame: {data['text'][:80]}")
    except WebSocketDisconnect:
        print(f"[WS] client disconnected after {chunk_n} chunks")
    except Exception as e:
        print(f"[WS] error: {e}")
