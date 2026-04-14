"""
Avatar / Sign Language Synthesis module.
Uses CWASA browser renderer via SiGML lookup.
"""

from dataclasses import dataclass
from avatar.sigml_lookup import text_to_sigml


@dataclass
class AvatarFrame:
    text: str
    sigml: str | None   # SiGML XML string for CWASA.playSiGMLText()
    url: str            # kept for backwards compat (placeholder)
    duration_ms: int


class SignAvatarEngine:
    AVATAR_PLACEHOLDER = "/static/avatar_placeholder.gif"

    def synthesize(self, text: str) -> AvatarFrame:
        sigml = text_to_sigml(text)
        duration_ms = max(1000, len(text.split()) * 500)
        return AvatarFrame(
            text=text,
            sigml=sigml,
            url=self.AVATAR_PLACEHOLDER,
            duration_ms=duration_ms,
        )


avatar_engine = SignAvatarEngine()
