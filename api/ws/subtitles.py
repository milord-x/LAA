import asyncio
import json
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

_connections: set[WebSocket] = set()


async def ws_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    _connections.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _connections.discard(websocket)


def broadcast_sync(payload: dict[str, Any]) -> None:
    """Called from pipeline thread — schedules async broadcast."""
    loop = _get_loop()
    if loop and loop.is_running():
        asyncio.run_coroutine_threadsafe(_broadcast(payload), loop)


async def _broadcast(payload: dict[str, Any]) -> None:
    dead: set[WebSocket] = set()
    for ws in list(_connections):
        try:
            await ws.send_text(json.dumps(payload, ensure_ascii=False))
        except Exception:
            dead.add(ws)
    _connections.difference_update(dead)


_loop_ref: asyncio.AbstractEventLoop | None = None


def set_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _loop_ref
    _loop_ref = loop


def _get_loop() -> asyncio.AbstractEventLoop | None:
    return _loop_ref
