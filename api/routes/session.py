from fastapi import APIRouter
from pydantic import BaseModel

from core.session import session_manager

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
    return SessionResponse(session_id=session.id, status="started")


@router.post("/stop", response_model=SessionResponse)
async def stop_session() -> SessionResponse:
    session = session_manager.stop_current()
    if session is None:
        return SessionResponse(session_id="", status="no_active_session")
    return SessionResponse(session_id=session.id, status="stopped")


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
