import time
import numpy as np
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

from asr.base import BaseASREngine, ASRChunk
from core.config import config

KAZ_RUS_MODEL_ID = "abilmansplus/whisper-turbo-kaz-rus-v1"


class KazRusEngine(BaseASREngine):
    def __init__(self) -> None:
        self._pipe = None
        self._language = config.ASR_LANGUAGE
        self._sample_rate = config.SAMPLE_RATE

    def load(self) -> None:
        print(f"[ASR] Loading KZ/RU model: {KAZ_RUS_MODEL_ID}")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if torch.cuda.is_available() else torch.float32

        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            KAZ_RUS_MODEL_ID,
            torch_dtype=dtype,
            low_cpu_mem_usage=True,
        ).to(device)

        processor = AutoProcessor.from_pretrained(KAZ_RUS_MODEL_ID)

        self._pipe = pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            torch_dtype=dtype,
            device=device,
        )
        print("[ASR] KZ/RU model loaded.")

    def transcribe_chunk(self, audio: bytes) -> ASRChunk:
        if self._pipe is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        audio_np = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0

        t0 = time.time()
        result = self._pipe({"array": audio_np, "sampling_rate": self._sample_rate})
        t1 = time.time()

        text = result.get("text", "").strip()
        return ASRChunk(text=text, start=t0, end=t1, language=self._language)
