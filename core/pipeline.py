"""
Orchestrates: microphone capture → ASR → structuring → broadcast via WebSocket.
"""

import asyncio
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

CHUNK_SAMPLES = config.SAMPLE_RATE * config.CHUNK_DURATION_SEC
FORMAT = pyaudio.paInt16
CHANNELS = 1


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
        stream = pa.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=config.SAMPLE_RATE,
            input=True,
            frames_per_buffer=1024,
        )

        frames: list[bytes] = []
        samples_collected = 0

        while self._running:
            data = stream.read(1024, exception_on_overflow=False)
            frames.append(data)
            samples_collected += 1024

            if samples_collected >= CHUNK_SAMPLES:
                audio_bytes = b"".join(frames)
                frames = []
                samples_collected = 0
                self._process(audio_bytes)

        stream.stop_stream()
        stream.close()
        pa.terminate()

    def _process(self, audio_bytes: bytes) -> None:
        session = session_manager.current()
        if session is None:
            return

        try:
            chunk = self._asr.transcribe_chunk(audio_bytes)
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
