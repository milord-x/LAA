"""
Avatar / Sign Language Synthesis module.
Translates RU/KZ -> EN, then maps to SiGML for CWASA.
"""

from dataclasses import dataclass
from avatar.sigml_lookup import text_to_sigml


@dataclass
class AvatarFrame:
    text: str
    sigml: str | None
    url: str
    duration_ms: int


class SignAvatarEngine:
    AVATAR_PLACEHOLDER = "/static/avatar_placeholder.gif"

    def synthesize(self, text: str) -> AvatarFrame:
        # Translate to EN for maximum sign coverage
        try:
            from avatar.translator import translate_to_en
            en_text = translate_to_en(text)
        except Exception:
            en_text = text

        sigml = text_to_sigml(en_text)
        duration_ms = max(1000, len(text.split()) * 500)
        return AvatarFrame(
            text=text,
            sigml=sigml,
            url=self.AVATAR_PLACEHOLDER,
            duration_ms=duration_ms,
        )


avatar_engine = SignAvatarEngine()
