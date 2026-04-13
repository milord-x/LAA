import time
import numpy as np
import whisper

from asr.base import BaseASREngine, ASRChunk
from core.config import config


class WhisperEngine(BaseASREngine):
    def __init__(self) -> None:
        self._model = None
        self._device = "cpu"
        self._model_name = config.ASR_MODEL
        self._language = config.ASR_LANGUAGE
        self._use_fp16 = False

    def load(self) -> None:
        import torch
        if torch.cuda.is_available():
            try:
                # Load on CPU in fp16, then move to GPU — uses ~1.5 GB VRAM instead of ~3.7 GB
                print(f"[ASR] Loading {self._model_name} on cuda (fp16)...")
                self._model = whisper.load_model(self._model_name, device="cpu")
                self._model = self._model.half().cuda()
                self._device = "cuda"
                self._use_fp16 = True
                vram = round(__import__("torch").cuda.memory_allocated() / 1024**3, 2)
                print(f"[ASR] Loaded on cuda, VRAM used: {vram} GB")
                return
            except Exception as e:
                print(f"[ASR] CUDA load failed ({e}), falling back to CPU")
                import torch as _torch
                _torch.cuda.empty_cache()

        print(f"[ASR] Loading {self._model_name} on cpu...")
        self._model = whisper.load_model(self._model_name, device="cpu")
        self._device = "cpu"
        self._use_fp16 = False
        print("[ASR] Loaded on cpu.")

    def transcribe_chunk(self, audio: bytes) -> ASRChunk:
        audio_np = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
        return self.transcribe_raw(audio_np)

    def transcribe_raw(self, audio_np: np.ndarray) -> ASRChunk:
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        t0 = time.time()

        if self._use_fp16:
            import torch
            with torch.amp.autocast("cuda"):
                result = self._model.transcribe(
                    audio_np,
                    language=self._language,
                    fp16=True,
                    task="transcribe",
                    condition_on_previous_text=False,
                )
        else:
            result = self._model.transcribe(
                audio_np,
                language=self._language,
                fp16=False,
                task="transcribe",
                condition_on_previous_text=False,
            )

        t1 = time.time()
        text = result.get("text", "").strip()
        print(f"[ASR] {t1-t0:.2f}s on {self._device} — {text!r}")
        return ASRChunk(text=text, start=t0, end=t1, language=self._language)
