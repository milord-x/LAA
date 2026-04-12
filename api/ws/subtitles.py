"""
Single WebSocket per session.
Browser sends raw PCM float32 LE (16kHz, mono) as binary frames.
Server responds with JSON subtitle payloads.
"""

import json
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect


async def ws_endpoint(websocket: WebSocket, process_audio_cb) -> None:
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive()
            if "bytes" in data and data["bytes"]:
                result = await process_audio_cb(data["bytes"])
                if result:
                    await websocket.send_text(
                        json.dumps(result, ensure_ascii=False)
                    )
            elif "text" in data:
                pass  # ignore text pings
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WS] error: {e}")
