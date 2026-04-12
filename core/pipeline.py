"""
Orchestrates: microphone capture → ASR → structuring → broadcast via WebSocket.
"""

import threading
import time
from typing import Callable

import pyaudio
import numpy as np

from asr.whisper_engine import WhisperEngine
from avatar.sync import sync_chunk, SyncedFrame
from core.config import config
from core.session import session_manager
from processing.structurer import structure_chunk

TARGET_RATE = config.SAMPLE_RATE  # 16000 Hz (Whisper wants this)
FORMAT = pyaudio.paInt16
CHANNELS = 1


def _get_device_rate(pa: pyaudio.PyAudio) -> int:
    """Return default input device sample rate."""
    try:
        info = pa.get_default_input_device_info()
        return int(info["defaultSampleRate"])
    except Exception:
        return TARGET_RATE


class Pipeline:
    def __init__(self) -> None:
        self._asr = WhisperEngine()
        self._model_loaded = False
        self._running = False
        self._thread: threading.Thread | None = None
        self._broadcast_cb: Callable[[dict], None] | None = None

    def set_broadcast(self, cb: Callable[[dict], None]) -> None:
        self._broadcast_cb = cb

    def start(self) -> None:
        if not self._model_loaded:
            self._asr.load()
            self._model_loaded = True
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _capture_loop(self) -> None:
        pa = pyaudio.PyAudio()
        device_rate = _get_device_rate(pa)
        print(f"[Pipeline] Device sample rate: {device_rate} Hz")

        chunk_samples = device_rate * config.CHUNK_DURATION_SEC

        stream = pa.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=device_rate,
            input=True,
            frames_per_buffer=1024,
        )

        frames: list[bytes] = []
        samples_collected = 0

        while self._running:
            data = stream.read(1024, exception_on_overflow=False)
            frames.append(data)
            samples_collected += 1024

            if samples_collected >= chunk_samples:
                audio_bytes = b"".join(frames)
                frames = []
                samples_collected = 0
                self._process(audio_bytes, device_rate)

        stream.stop_stream()
        stream.close()
        pa.terminate()

    def _process(self, audio_bytes: bytes, device_rate: int) -> None:
        session = session_manager.current()
        if session is None:
            return

        audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

        # Resample to 16000 Hz if needed
        if device_rate != TARGET_RATE:
            ratio = TARGET_RATE / device_rate
            new_len = int(len(audio_np) * ratio)
            indices = np.linspace(0, len(audio_np) - 1, new_len)
            audio_np = np.interp(indices, np.arange(len(audio_np)), audio_np)

        try:
            chunk = self._asr.transcribe_raw(audio_np)
        except Exception as e:
            print(f"[Pipeline] ASR error: {e}")
            return

        if not chunk.text:
            return

        session.append_text(chunk.text)
        structured = structure_chunk(chunk.text)
        synced: SyncedFrame = sync_chunk(chunk.text, timestamp=chunk.start)

        payload = {
            "type": "subtitle",
            "text": chunk.text,
            "keywords": structured["keywords"],
            "avatar_url": synced.avatar_url,
            "avatar_duration_ms": synced.duration_ms,
            "timestamp": chunk.start,
        }

        if self._broadcast_cb:
            self._broadcast_cb(payload)


pipeline = Pipeline()
