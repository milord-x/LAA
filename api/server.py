import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from fastapi import WebSocket

from api.routes import session as session_routes
from api.routes import summary as summary_routes
from api.ws.subtitles import ws_endpoint, set_event_loop
from core.pipeline import pipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    set_event_loop(loop)
    pipeline.set_broadcast(__import__("api.ws.subtitles", fromlist=["broadcast_sync"]).broadcast_sync)
    yield


app = FastAPI(title="LAA — Lecture Access Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(session_routes.router)
app.include_router(summary_routes.router)

@app.websocket("/ws/subtitles")
async def websocket_subtitles(websocket: WebSocket) -> None:
    await ws_endpoint(websocket)

frontend_dir = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(str(frontend_dir / "index.html"))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
