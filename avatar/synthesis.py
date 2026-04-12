"""
Avatar / Sign Language Synthesis module.

Current implementation: stub that returns a placeholder URL per text chunk.
Replace with real SignLanguageSynthesis pipeline when available.

Integration points:
  - synthesis.synthesize(text) -> AvatarFrame
  - AvatarFrame.url  : URL or base64 data for frontend to render
  - AvatarFrame.duration_ms : estimated play duration
"""

import hashlib
from dataclasses import dataclass


@dataclass
class AvatarFrame:
    text: str
    url: str
    duration_ms: int


class SignAvatarEngine:
    """Stub avatar engine. Swap _render() for real pipeline."""

    AVATAR_PLACEHOLDER = "/static/avatar_placeholder.gif"

    def synthesize(self, text: str) -> AvatarFrame:
        url = self._render(text)
        duration_ms = max(1000, len(text.split()) * 400)
        return AvatarFrame(text=text, url=url, duration_ms=duration_ms)

    def _render(self, text: str) -> str:
        # TODO: replace with SignLanguageSynthesis API call
        # e.g. POST to local SLS service, get back video URL
        _ = hashlib.md5(text.encode()).hexdigest()
        return self.AVATAR_PLACEHOLDER


avatar_engine = SignAvatarEngine()
