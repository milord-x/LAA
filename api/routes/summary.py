from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.session import session_manager
from processing.summarizer import generate_summary

router = APIRouter(prefix="/summary", tags=["summary"])


class SummaryResponse(BaseModel):
    session_id: str
    summary: str
    transcript_preview: str


@router.get("/{session_id}", response_model=SummaryResponse)
async def get_summary(session_id: str) -> SummaryResponse:
    session = session_manager.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.active:
        raise HTTPException(status_code=400, detail="Session still active. Stop it first.")

    if session.summary is None:
        session.summary = generate_summary(session.full_transcript())

    preview = session.full_transcript()[:300]

    return SummaryResponse(
        session_id=session.id,
        summary=session.summary,
        transcript_preview=preview,
    )


@router.get("/current/live")
async def live_transcript() -> dict:
    session = session_manager.current()
    if session is None:
        return {"text": "", "active": False}
    return {
        "text": session.full_transcript(),
        "active": session.active,
        "chunks": len(session.transcript),
    }
