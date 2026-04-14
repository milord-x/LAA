from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.routes import session as session_routes
from api.routes import summary as summary_routes
from api.ws.subtitles import ws_endpoint
from core.pipeline import pipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    print("[Server] Pre-loading ASR model...")
    await asyncio.get_event_loop().run_in_executor(None, pipeline.ensure_loaded)
    print("[Server] ASR model ready.")
    yield


app = FastAPI(title="LAA — Lecture Access Agent", lifespan=lifespan)

# NOTE: CORSMiddleware is intentionally omitted — it breaks WebSocket in Starlette 1.0.
# Frontend is served from the same origin so CORS is not needed.

app.include_router(session_routes.router)
app.include_router(summary_routes.router)


@app.websocket("/ws/subtitles")
async def websocket_subtitles(websocket: WebSocket) -> None:
    await ws_endpoint(websocket, pipeline.process_bytes)


frontend_dir = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(str(frontend_dir / "index.html"))


@app.get("/cwaclientcfg.json")
async def cwasa_config() -> FileResponse:
    """CWASA looks for this file at the page root."""
    return FileResponse(str(frontend_dir / "cwaclientcfg.json"), media_type="application/json")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
