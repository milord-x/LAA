"""
Extractive summarizer — fully offline, no API keys required.

Algorithm:
  1. Split transcript into sentences.
  2. Score each sentence by keyword frequency (TF-style).
  3. Pick top-N sentences in original order.
  4. Return structured text block.
"""

import re
from processing.structurer import extract_keywords


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in parts if len(s.strip()) > 10]


def _score_sentences(sentences: list[str], keywords: list[str]) -> list[tuple[int, float]]:
    kw_set = set(keywords)
    scored: list[tuple[int, float]] = []
    for idx, sentence in enumerate(sentences):
        words = re.findall(r"\b[а-яёА-ЯЁa-zA-Z]+\b", sentence.lower())
        hits = sum(1 for w in words if w in kw_set)
        score = hits / max(len(words), 1)
        scored.append((idx, score))
    return scored


def generate_summary(transcript: str, top_n: int = 5) -> str:
    if not transcript.strip():
        return "Транскрипт пустой."

    sentences = _split_sentences(transcript)
    if not sentences:
        return transcript[:500]

    keywords = extract_keywords(transcript, max_keywords=20)
    scored = _score_sentences(sentences, keywords)

    top_indices = sorted(
        sorted(scored, key=lambda x: x[1], reverse=True)[:top_n],
        key=lambda x: x[0],
    )

    top_sentences = [sentences[i] for i, _ in top_indices]

    kw_line = ", ".join(keywords[:8]) if keywords else "—"
    summary_body = " ".join(top_sentences)

    return f"Ключевые темы: {kw_line}.\n\n{summary_body}"
