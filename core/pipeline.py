"""
Audio processor: parse frame → resample → VAD → ASR → filter → return subtitle.

Wire protocol (8-byte header):
  Bytes 0-3: uint32 BE 0x4C414100 ("LAA\0")
  Bytes 4-7: uint32 LE sample rate
  Bytes 8+:  float32 LE mono PCM
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

SILENCE_RMS = float(__import__("os").getenv("SILENCE_RMS", "0.002"))

HEADER_MAGIC = 0x4C414100
HEADER_SIZE = 8

_HALLUCINATIONS_EXACT = {
    "продолжение следует", "субтитры сделаны", "субтитры",
    "thanks for watching", "thank you for watching", "subscribe",
    "да", "нет", "ок", "окей", "хорошо", "ладно",
    "yes", "no", "ok", "okay", "hmm", "uh", "um",
    "music", "музыка", "аплодисменты", "смех",
}

_HALLUCINATIONS_SUBSTR = [
    "субтитры создавал", "субтитры сделал", "продолжение следует",
    "dimatzrok", "dimatorzok", "редактор субтитров",
    "динамичная музыка", "бойный стучок",
]


def _parse_frame(raw: bytes) -> tuple[np.ndarray, int]:
    if len(raw) >= HEADER_SIZE:
        magic = struct.unpack_from(">I", raw, 0)[0]
        if magic == HEADER_MAGIC:
            src_rate = struct.unpack_from("<I", raw, 4)[0]
            audio_np = np.frombuffer(raw[HEADER_SIZE:], dtype=np.float32).copy()
            print(f"[Pipeline] src_rate={src_rate} samples={audio_np.size}")
            return audio_np, src_rate
    audio_np = np.frombuffer(raw, dtype=np.float32).copy()
    print(f"[Pipeline] no header, assuming {TARGET_RATE} Hz")
    return audio_np, TARGET_RATE


def _resample(audio: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    if src_rate == dst_rate:
        return audio
    try:
        import torch
        import torchaudio.functional as F
        t = torch.from_numpy(audio).unsqueeze(0)
        out = F.resample(t, src_rate, dst_rate).squeeze(0).numpy()
        print(f"[Pipeline] resampled {len(audio)}@{src_rate} → {len(out)}@{dst_rate}")
        return out.astype(np.float32)
    except Exception as e:
        print(f"[Pipeline] torchaudio failed ({e}), linear interp")
        n = int(len(audio) * dst_rate / src_rate)
        return np.interp(np.linspace(0, len(audio)-1, n), np.arange(len(audio)), audio).astype(np.float32)


def _is_silence(audio: np.ndarray) -> tuple[bool, float]:
    rms = float(np.sqrt(np.mean(audio ** 2)))
    return rms < SILENCE_RMS, rms


def _is_hallucination(text: str) -> bool:
    t = text.strip().lower().strip(".,!?-– …[]()\"'")
    if len(t) < 4:
        return True
    if t in _HALLUCINATIONS_EXACT:
        return True
    for s in _HALLUCINATIONS_SUBSTR:
        if s in t:
            return True
    return False


class Pipeline:
    def __init__(self) -> None:
        self._asr = WhisperEngine()
        self._model_loaded = False
        self._vad = None          # silero VAD model
        self._vad_utils = None
        self._last_text = ""      # for deduplication

    def ensure_loaded(self) -> None:
        if not self._model_loaded:
            self._asr.load()
            self._load_vad()
            self._model_loaded = True

    def _load_vad(self) -> None:
        try:
            import torch
            model, utils = torch.hub.load(
                "snakers4/silero-vad", "silero_vad",
                trust_repo=True, verbose=False,
            )
            self._vad = model
            self._vad_utils = utils
            print("[Pipeline] Silero VAD loaded")
        except Exception as e:
            print(f"[Pipeline] VAD load failed ({e}), using RMS only")

    def _has_speech(self, audio: np.ndarray) -> bool:
        """Run silero VAD on 16kHz mono float32. Returns True if speech detected."""
        if self._vad is None:
            return True  # fallback: trust RMS gate
        try:
            import torch
            tensor = torch.from_numpy(audio)
            # Silero needs chunks of 512 or 1024 samples at 16kHz
            window = 512
            speech_frames = 0
            total_frames = 0
            for i in range(0, len(tensor) - window, window):
                chunk = tensor[i:i + window]
                prob = self._vad(chunk, 16000).item()
                if prob > 0.5:
                    speech_frames += 1
                total_frames += 1
            if total_frames == 0:
                return False
            ratio = speech_frames / total_frames
            print(f"[VAD] speech_ratio={ratio:.2f} ({speech_frames}/{total_frames} frames)")
            return ratio > 0.15  # at least 15% of frames must be speech
        except Exception as e:
            print(f"[VAD] error: {e}")
            return True

    def _is_duplicate(self, text: str) -> bool:
        """Drop chunk if it's nearly identical to the previous one."""
        t = text.strip().lower()
        p = self._last_text.strip().lower()
        if not p:
            return False
        # Simple: if one contains the other almost entirely
        if t == p:
            return True
        if len(t) > 10 and len(p) > 10:
            shorter, longer = (t, p) if len(t) <= len(p) else (p, t)
            if shorter in longer:
                return True
        return False

    async def process_bytes(self, raw: bytes) -> dict | None:
        if not self._model_loaded:
            print("[Pipeline] model not loaded, dropping chunk")
            return None

        session = session_manager.current()
        if session is None:
            print("[Pipeline] no active session")
            return None

        audio_np, src_rate = _parse_frame(raw)
        if audio_np.size == 0:
            return None

        if src_rate != TARGET_RATE:
            audio_np = _resample(audio_np, src_rate, TARGET_RATE)

        # Gate 1: RMS (fast, catches complete silence)
        silent, rms = _is_silence(audio_np)
        print(f"[Pipeline] RMS={rms:.5f} silence={silent}")
        if silent:
            print("[Pipeline] dropped — silence")
            return None

        # Gate 2: VAD (catches noise/music/non-speech)
        loop = asyncio.get_running_loop()
        has_speech = await loop.run_in_executor(None, self._has_speech, audio_np)
        if not has_speech:
            print("[Pipeline] dropped — VAD: no speech detected")
            return None

        # ASR
        t0 = time.time()
        try:
            chunk = await loop.run_in_executor(None, self._asr.transcribe_raw, audio_np)
        except Exception as e:
            print(f"[Pipeline] ASR error: {e}")
            return None
        print(f"[Pipeline] ASR {time.time()-t0:.2f}s — {chunk.text!r}")

        # Gate 3: hallucination filter
        if not chunk.text or _is_hallucination(chunk.text):
            print(f"[Pipeline] dropped — hallucination: {chunk.text!r}")
            return None

        # Gate 4: deduplication
        if self._is_duplicate(chunk.text):
            print(f"[Pipeline] dropped — duplicate: {chunk.text!r}")
            return None
        self._last_text = chunk.text

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
