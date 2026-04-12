from openai import OpenAI

from core.config import config

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _client


def generate_summary(transcript: str) -> str:
    if not transcript.strip():
        return "Транскрипт пустой."

    client = _get_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Ты — ассистент для слабослышащих пользователей. "
                    "Составь краткое структурированное резюме лекции или речи. "
                    "Выдели ключевые темы, основные мысли и важные факты. "
                    "Отвечай на русском языке."
                ),
            },
            {
                "role": "user",
                "content": f"Транскрипт:\n{transcript}",
            },
        ],
        max_tokens=600,
        temperature=0.3,
    )

    return response.choices[0].message.content.strip()
