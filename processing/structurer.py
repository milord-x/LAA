import re


def extract_keywords(text: str, max_keywords: int = 10) -> list[str]:
    """Simple frequency-based keyword extraction (no external deps)."""
    stopwords = {
        "и", "в", "на", "с", "по", "из", "для", "это", "что", "как",
        "но", "а", "же", "от", "к", "или", "не", "то", "так", "при",
        "он", "она", "они", "мы", "вы", "я", "его", "её", "их",
        "the", "a", "an", "is", "are", "was", "were", "of", "in", "to",
    }

    words = re.findall(r"\b[а-яёА-ЯЁa-zA-Z]{4,}\b", text.lower())
    freq: dict[str, int] = {}
    for word in words:
        if word not in stopwords:
            freq[word] = freq.get(word, 0) + 1

    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in sorted_words[:max_keywords]]


def structure_chunk(text: str) -> dict:
    """Return enriched metadata for a transcript chunk."""
    return {
        "text": text,
        "keywords": extract_keywords(text, max_keywords=5),
        "word_count": len(text.split()),
    }
