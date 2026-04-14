from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.session import session_manager
from core.pipeline import pipeline

router = APIRouter(prefix="/session", tags=["session"])


class SessionResponse(BaseModel):
    session_id: str
    status: str


@router.post("/start", response_model=SessionResponse)
async def start_session() -> SessionResponse:
    existing = session_manager.current()
    if existing and existing.active:
        return SessionResponse(session_id=existing.id, status="already_running")

    session = session_manager.create()
    pipeline.reset_state()
    return SessionResponse(session_id=session.id, status="started")


@router.post("/stop", response_model=SessionResponse)
async def stop_session() -> SessionResponse:
    session = session_manager.stop_current()
    if session is None:
        return SessionResponse(session_id="", status="no_active_session")
    return SessionResponse(session_id=session.id, status="stopped")


_VALID_MODES = {"auto", "ru", "en", "kz"}


@router.post("/mode/{mode}")
async def set_mode(mode: str) -> dict:
    if mode not in _VALID_MODES:
        raise HTTPException(status_code=400, detail=f"Invalid mode. Use: {_VALID_MODES}")
    import asyncio
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, pipeline._asr.set_mode, mode)
    pipeline.reset_state()  # clear dedup cache on lang switch
    return {"mode": mode}


@router.get("/mode")
async def get_mode() -> dict:
    return {"mode": pipeline._asr._mode}


@router.get("/status")
async def session_status() -> dict:
    session = session_manager.current()
    if session is None:
        return {"active": False}
    return {
        "active": session.active,
        "session_id": session.id,
        "transcript_chunks": len(session.transcript),
    }
