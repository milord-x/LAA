import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    ASR_MODEL: str = os.getenv("ASR_MODEL", "large-v3-turbo")
    ASR_LANGUAGE: str = os.getenv("ASR_LANGUAGE", "ru")
    CHUNK_DURATION_SEC: int = int(os.getenv("CHUNK_DURATION_SEC", "3"))
    SAMPLE_RATE: int = int(os.getenv("SAMPLE_RATE", "16000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))


config = Config()
