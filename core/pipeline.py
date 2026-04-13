"""
Stateless audio processor.
Receives float32 PCM numpy array, resamples to 16kHz mono if needed, returns subtitle payload dict.
Audio capture is done in the browser; no PyAudio needed.

Wire protocol from frontend:
  - Byte 0:     0xAA  (magic marker)
  - Bytes 1-4:  uint32 LE  — actual sample rate reported by AudioWorklet
  - Bytes 5+:   float32 LE PCM samples (mono)

If magic is missing the frame is treated as raw 16kHz float32 (legacy fallback).
"""

import asyncio
import struct
import time

import numpy as np

from asr.whisper_engine import WhisperEngine
from avatar.sync import sync_chunk, SyncedFrame
from core.config import config
from core.session import session_manager
from processing.structurer import structure_chunk

TARGET_RATE = config.SAMPLE_RATE  # 16000

# RMS threshold — intentionally low so quiet-but-real speech is not dropped.
# Adjust via env SILENCE_RMS if needed.
SILENCE_RMS = float(__import__("os").getenv("SILENCE_RMS", "0.002"))

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

HEADER_MAGIC = 0xAA
HEADER_SIZE = 5  # 1 byte magic + 4 bytes uint32


def _parse_frame(raw: bytes) -> tuple[np.ndarray, int]:
    """
    Returns (float32 mono array, source_sample_rate).
    Handles both the new headered protocol and the legacy raw-float32 format.
    """
    if len(raw) >= HEADER_SIZE and raw[0] == HEADER_MAGIC:
        src_rate = struct.unpack_from("<I", raw, 1)[0]
        audio_np = np.frombuffer(raw[HEADER_SIZE:], dtype=np.float32).copy()
        print(f"[Pipeline] header OK — src_rate={src_rate} samples={audio_np.size}")
    else:
        # Legacy: assume raw float32 at 16000 Hz
        src_rate = TARGET_RATE
        audio_np = np.frombuffer(raw, dtype=np.float32).copy()
        print(f"[Pipeline] no header — assuming {src_rate} Hz, samples={audio_np.size}")
    return audio_np, src_rate


def _resample(audio: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    """Linear-interpolation resample. Good enough for speech; avoids scipy dependency."""
    if src_rate == dst_rate:
        return audio
    duration = len(audio) / src_rate
    n_dst = int(duration * dst_rate)
    x_src = np.linspace(0, len(audio) - 1, n_dst)
    resampled = np.interp(x_src, np.arange(len(audio)), audio).astype(np.float32)
    print(f"[Pipeline] resampled {len(audio)}@{src_rate}Hz → {len(resampled)}@{dst_rate}Hz")
    return resampled


def _is_silence(audio: np.ndarray) -> tuple[bool, float]:
    rms = float(np.sqrt(np.mean(audio ** 2)))
    return rms < SILENCE_RMS, rms


def _is_hallucination(text: str) -> bool:
    t = text.strip().lower().rstrip(".")
    return t in _HALLUCINATIONS or len(t) < 2


class Pipeline:
    def __init__(self) -> None:
        self._asr = WhisperEngine()
        self._model_loaded = False
        self._executor = None  # lazy thread pool for blocking ASR

    def ensure_loaded(self) -> None:
        if not self._model_loaded:
            self._asr.load()
            self._model_loaded = True

    async def process_bytes(self, raw: bytes) -> dict | None:
        """
        raw: binary frame from browser (headered or legacy float32 PCM).
        Returns subtitle payload or None if nothing transcribed.
        """
        self.ensure_loaded()

        session = session_manager.current()
        if session is None:
            return None

        audio_np, src_rate = _parse_frame(raw)

        if audio_np.size == 0:
            return None

        # Resample to 16kHz if browser delivered a different rate
        if src_rate != TARGET_RATE:
            audio_np = _resample(audio_np, src_rate, TARGET_RATE)

        silent, rms = _is_silence(audio_np)
        print(f"[Pipeline] RMS={rms:.5f} threshold={SILENCE_RMS:.5f} silence={silent}")
        if silent:
            print("[Pipeline] chunk dropped — below silence threshold")
            return None

        # Run blocking Whisper in a thread so we don't stall the event loop
        loop = asyncio.get_event_loop()
        t0 = time.time()
        try:
            chunk = await loop.run_in_executor(None, self._asr.transcribe_raw, audio_np)
        except Exception as e:
            print(f"[Pipeline] ASR error: {e}")
            return None
        elapsed = time.time() - t0
        print(f"[Pipeline] ASR done in {elapsed:.2f}s — text={chunk.text!r}")

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
