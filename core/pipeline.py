"""
Stateless audio processor.
Receives float32 PCM numpy array, resamples to 16kHz mono if needed, returns subtitle payload dict.

Wire protocol from frontend (8-byte header):
  - Bytes 0-3:  uint32 BE  0x4C414100  ("LAA\0") — magic marker
  - Bytes 4-7:  uint32 LE  — actual sample rate reported by AudioWorklet
  - Bytes 8+:   float32 LE PCM samples (mono)

If magic is absent the frame is treated as raw float32 at TARGET_RATE (fallback).
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

# RMS threshold — keep low so quiet speech is not dropped.
# Override with env SILENCE_RMS=0.001 etc.
SILENCE_RMS = float(__import__("os").getenv("SILENCE_RMS", "0.002"))

HEADER_MAGIC = 0x4C414100  # "LAA\0" as uint32 big-endian
HEADER_SIZE = 8             # 4 bytes magic + 4 bytes uint32 sample rate

# Whisper hallucinations — single-word/short outputs Whisper emits for silence/noise
_HALLUCINATIONS = {
    "продолжение следует", "субтитры сделаны", "субтитры",
    "thanks for watching", "thank you for watching", "subscribe",
    "...", ".", ",", "-", "–",
    "да", "нет", "ок", "окей", "хорошо", "ладно",
    "yes", "no", "ok", "okay", "hmm", "uh", "um",
}


def _parse_frame(raw: bytes) -> tuple[np.ndarray, int]:
    """Return (float32 mono array, source_sample_rate)."""
    if len(raw) >= HEADER_SIZE:
        magic = struct.unpack_from(">I", raw, 0)[0]
        if magic == HEADER_MAGIC:
            src_rate = struct.unpack_from("<I", raw, 4)[0]
            audio_np = np.frombuffer(raw[HEADER_SIZE:], dtype=np.float32).copy()
            print(f"[Pipeline] header OK — src_rate={src_rate} samples={audio_np.size}")
            return audio_np, src_rate

    # Fallback: legacy raw float32 at TARGET_RATE
    audio_np = np.frombuffer(raw, dtype=np.float32).copy()
    print(f"[Pipeline] no header — assuming {TARGET_RATE} Hz, samples={audio_np.size}")
    return audio_np, TARGET_RATE


def _resample(audio: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    """Resample using torchaudio sinc filter — correct quality for ASR."""
    if src_rate == dst_rate:
        return audio
    try:
        import torch
        import torchaudio.functional as F
        tensor = torch.from_numpy(audio).unsqueeze(0)  # (1, N)
        resampled = F.resample(tensor, src_rate, dst_rate).squeeze(0).numpy()
        print(f"[Pipeline] resampled {len(audio)}@{src_rate} → {len(resampled)}@{dst_rate}")
        return resampled.astype(np.float32)
    except Exception as e:
        # Fallback to linear interpolation if torchaudio fails
        print(f"[Pipeline] torchaudio resample failed ({e}), using linear interp")
        n_dst = int(len(audio) * dst_rate / src_rate)
        x_src = np.linspace(0, len(audio) - 1, n_dst)
        return np.interp(x_src, np.arange(len(audio)), audio).astype(np.float32)


def _is_silence(audio: np.ndarray) -> tuple[bool, float]:
    rms = float(np.sqrt(np.mean(audio ** 2)))
    return rms < SILENCE_RMS, rms


def _is_hallucination(text: str) -> bool:
    t = text.strip().lower().strip(".,!?-– ")
    return t in _HALLUCINATIONS or len(t) < 3


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
        raw: binary frame from browser.
        Model must already be loaded (preloaded in lifespan).
        Returns subtitle payload or None.
        """
        if not self._model_loaded:
            print("[Pipeline] WARNING: model not loaded, dropping chunk")
            return None

        session = session_manager.current()
        if session is None:
            print("[Pipeline] no active session, dropping chunk")
            return None

        audio_np, src_rate = _parse_frame(raw)
        if audio_np.size == 0:
            return None

        if src_rate != TARGET_RATE:
            audio_np = _resample(audio_np, src_rate, TARGET_RATE)

        silent, rms = _is_silence(audio_np)
        print(f"[Pipeline] RMS={rms:.5f} threshold={SILENCE_RMS:.5f} silence={silent}")
        if silent:
            print("[Pipeline] chunk dropped — silence")
            return None

        loop = asyncio.get_event_loop()
        t0 = time.time()
        try:
            chunk = await loop.run_in_executor(None, self._asr.transcribe_raw, audio_np)
        except Exception as e:
            print(f"[Pipeline] ASR error: {e}")
            return None
        elapsed = time.time() - t0
        print(f"[Pipeline] ASR {elapsed:.2f}s — text={chunk.text!r}")

        if not chunk.text or _is_hallucination(chunk.text):
            print(f"[Pipeline] dropped hallucination/empty: {chunk.text!r}")
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
