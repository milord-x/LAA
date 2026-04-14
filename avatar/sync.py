from dataclasses import dataclass

from avatar.synthesis import AvatarFrame, avatar_engine


@dataclass
class SyncedFrame:
    text: str
    avatar_url: str
    avatar_sigml: str | None
    duration_ms: int
    timestamp: float


def sync_chunk(text: str, timestamp: float) -> SyncedFrame:
    """Produce a synced subtitle + avatar frame for a given text chunk."""
    frame: AvatarFrame = avatar_engine.synthesize(text)
    return SyncedFrame(
        text=text,
        avatar_url=frame.url,
        avatar_sigml=frame.sigml,
        duration_ms=frame.duration_ms,
        timestamp=timestamp,
    )
