import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Session:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    transcript: list[str] = field(default_factory=list)
    summary: Optional[str] = None
    active: bool = True

    def append_text(self, text: str) -> None:
        self.transcript.append(text)

    def stop(self) -> None:
        self.active = False
        self.ended_at = datetime.utcnow()

    def full_transcript(self) -> str:
        return " ".join(self.transcript)


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._current: Optional[str] = None

    def create(self) -> Session:
        # Force-stop any lingering active session before creating a new one
        existing = self.current()
        if existing and existing.active:
            existing.stop()
        session = Session()
        self._sessions[session.id] = session
        self._current = session.id
        return session

    def current(self) -> Optional[Session]:
        if self._current:
            return self._sessions.get(self._current)
        return None

    def get(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def stop_current(self) -> Optional[Session]:
        session = self.current()
        if session:
            session.stop()
            self._current = None
        return session


session_manager = SessionManager()
