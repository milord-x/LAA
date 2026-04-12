import time
import numpy as np
import whisper

from asr.base import BaseASREngine, ASRChunk
from core.config import config


class WhisperEngine(BaseASREngine):
    def __init__(self) -> None:
        self._model = None
        self._model_name = config.ASR_MODEL
        self._language = config.ASR_LANGUAGE

    def load(self) -> None:
        print(f"[ASR] Loading Whisper model: {self._model_name} on CPU")
        self._model = whisper.load_model(self._model_name, device="cpu")
        print("[ASR] Model loaded.")

    def transcribe_chunk(self, audio: bytes) -> ASRChunk:
        audio_np = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
        return self.transcribe_raw(audio_np)

    def transcribe_raw(self, audio_np: np.ndarray) -> ASRChunk:
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        t0 = time.time()
        result = self._model.transcribe(
            audio_np,
            language=self._language,
            fp16=False,
        )
        t1 = time.time()

        text = result.get("text", "").strip()
        return ASRChunk(text=text, start=t0, end=t1, language=self._language)
