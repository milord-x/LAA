"""
Stateless audio processor.
Receives float32 PCM numpy array (16kHz mono), returns subtitle payload dict.
Audio capture is done in the browser; no PyAudio needed.
"""

import numpy as np

from asr.whisper_engine import WhisperEngine
from avatar.sync import sync_chunk, SyncedFrame
from core.config import config
from core.session import session_manager
from processing.structurer import structure_chunk

TARGET_RATE = config.SAMPLE_RATE  # 16000

# RMS threshold below which audio is considered silence
SILENCE_RMS = 0.01

# Whisper hallucination patterns to discard
_HALLUCINATIONS = {
    "продолжение следует",
    "субтитры сделаны",
    "субтитры",
    "thanks for watching",
    "thank you for watching",
    "subscribe",
    "...",
    ".",
}


def _is_silence(audio: np.ndarray) -> bool:
    rms = float(np.sqrt(np.mean(audio ** 2)))
    return rms < SILENCE_RMS


def _is_hallucination(text: str) -> bool:
    t = text.strip().lower().rstrip(".")
    return t in _HALLUCINATIONS or len(t) < 2


class Pipeline:
    def __init__(self) -> None:
        self._asr = WhisperEngine()
        self._model_loaded = False

    def ensure_loaded(self) -> None:
        if not self._model_loaded:
            self._asr.load()
            self._model_loaded = True

    async def process_bytes(self, raw: bytes) -> dict | None:
        """
        raw: PCM float32 LE bytes from browser (16kHz mono).
        Returns subtitle payload or None if nothing transcribed.
        """
        self.ensure_loaded()

        session = session_manager.current()
        if session is None:
            return None

        audio_np = np.frombuffer(raw, dtype=np.float32).copy()

        if audio_np.size == 0 or _is_silence(audio_np):
            return None

        try:
            chunk = self._asr.transcribe_raw(audio_np)
        except Exception as e:
            print(f"[Pipeline] ASR error: {e}")
            return None

        if not chunk.text or _is_hallucination(chunk.text):
            return None

        session.append_text(chunk.text)
        structured = structure_chunk(chunk.text)
        synced: SyncedFrame = sync_chunk(chunk.text, timestamp=chunk.start)

        return {
            "type": "subtitle",
            "text": chunk.text,
            "keywords": structured["keywords"],
            "avatar_url": synced.avatar_url,
            "avatar_duration_ms": synced.duration_ms,
            "timestamp": chunk.start,
        }


pipeline = Pipeline()
