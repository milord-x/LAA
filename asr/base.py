from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ASRChunk:
    text: str
    start: float
    end: float
    language: str = "ru"


class BaseASREngine(ABC):
    @abstractmethod
    def transcribe_chunk(self, audio: bytes) -> ASRChunk:
        """Transcribe raw PCM audio bytes, return ASRChunk."""
        ...

    @abstractmethod
    def load(self) -> None:
        """Load model into memory."""
        ...
