import json
from fastapi import WebSocket, WebSocketDisconnect


async def ws_endpoint(websocket: WebSocket, process_audio_cb) -> None:
    await websocket.accept()
    chunk_n = 0
    print("[WS] connected")
    try:
        while True:
            # receive_bytes() is the correct Starlette 1.0 API for binary frames
            raw = await websocket.receive_bytes()
            chunk_n += 1
            print(f"[WS] chunk #{chunk_n} bytes={len(raw)} first8={raw[:8].hex()}")
            result = await process_audio_cb(raw)
            if result:
                await websocket.send_text(json.dumps(result, ensure_ascii=False))
    except WebSocketDisconnect:
        print(f"[WS] client disconnected after {chunk_n} chunks")
    except Exception as e:
        import traceback
        print(f"[WS] error: {type(e).__name__}: {e}")
        traceback.print_exc()
