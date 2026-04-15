"""
Optional LLM refinement layer for the LAA agent pipeline.

Activated only when LAA_ENABLE_LLM=true is set in environment.
Uses any OpenAI-compatible HTTP API (OpenAI, local llama.cpp, Ollama, etc.)
with a simple httpx-based client — no openai SDK required.

Architecture position:
    ASR → structuring → agent policy → [LLM refiner] → outputs

The refiner does NOT replace agent policy. It runs after routing decisions
are made and can:
  - Rewrite raw transcript into cleaner, more accessible text
  - Condense long speech blocks (>20 words) into concise summaries
  - Generate structured notes from topic-ending blocks

If LLM is unavailable, times out, or returns an error, the original
text passes through unchanged. Offline mode is always preserved.
"""

import asyncio
import json
import logging
import os
import time
from typing import Optional

logger = logging.getLogger("laa.llm")

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------

_ENABLED: bool = os.getenv("LAA_ENABLE_LLM", "false").lower() == "true"
_PROVIDER: str = os.getenv("LAA_LLM_PROVIDER", "openai_compatible")
_MODEL: str = os.getenv("LAA_LLM_MODEL", "gpt-4o-mini")
_BASE_URL: str = os.getenv("LAA_LLM_BASE_URL", "https://api.openai.com/v1")
_API_KEY: str = os.getenv("LAA_LLM_API_KEY", "")
_TIMEOUT: float = float(os.getenv("LAA_LLM_TIMEOUT", "5.0"))
_MAX_TOKENS: int = int(os.getenv("LAA_LLM_MAX_TOKENS", "120"))

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_REFINE_PROMPT = (
    "You are an accessibility assistant. Rewrite the following speech segment "
    "into clean, clear text for hearing-impaired users. "
    "Remove filler words. Keep the meaning. Output only the rewritten text, nothing else.\n\n"
    "Segment: {text}"
)

_CONDENSE_PROMPT = (
    "You are an accessibility assistant. Condense the following speech block "
    "into 1-2 clear sentences suitable for subtitles. "
    "Preserve key information. Output only the condensed text.\n\n"
    "Block: {text}"
)

_STRUCTURED_NOTE_PROMPT = (
    "You are an accessibility assistant helping hearing-impaired students. "
    "Extract a short structured note (1-3 bullet points) from this lecture segment. "
    "Output only the bullet points.\n\n"
    "Segment: {text}"
)


# ---------------------------------------------------------------------------
# HTTP client (no openai SDK dependency)
# ---------------------------------------------------------------------------

async def _call_llm(prompt: str) -> Optional[str]:
    """
    Send a single-turn chat completion request to an OpenAI-compatible API.
    Returns the response text or None on any failure.
    """
    if not _API_KEY:
        logger.warning("LAA_LLM_API_KEY not set — skipping LLM call")
        return None

    try:
        import httpx
    except ImportError:
        logger.warning("httpx not installed — LLM calls disabled. pip install httpx")
        return None

    url = f"{_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": _MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": _MAX_TOKENS,
        "temperature": 0.3,
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning("LLM call failed (%s: %s) — falling back to original text", type(e).__name__, e)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def refine_text(text: str) -> str:
    """
    Rewrite a short segment into clean accessible text.
    Falls back to original text if LLM is disabled or fails.
    """
    if not _ENABLED:
        return text
    t0 = time.monotonic()
    result = await _call_llm(_REFINE_PROMPT.format(text=text))
    elapsed = (time.monotonic() - t0) * 1000
    if result:
        logger.info("refine OK %.0fms | %r → %r", elapsed, text[:40], result[:40])
        return result
    return text


async def condense_block(text: str) -> str:
    """
    Condense a long speech block (>20 words) into 1-2 sentences.
    Falls back to original text if LLM is disabled or fails.
    """
    if not _ENABLED:
        return text
    t0 = time.monotonic()
    result = await _call_llm(_CONDENSE_PROMPT.format(text=text))
    elapsed = (time.monotonic() - t0) * 1000
    if result:
        logger.info("condense OK %.0fms | len=%d → %d chars", elapsed, len(text), len(result))
        return result
    return text


async def generate_structured_note(text: str) -> Optional[str]:
    """
    Generate bullet-point structured notes from a topic-ending segment.
    Returns None if LLM is disabled or fails (caller uses extractive summary instead).
    """
    if not _ENABLED:
        return None
    result = await _call_llm(_STRUCTURED_NOTE_PROMPT.format(text=text))
    return result


def is_enabled() -> bool:
    """Return True when LLM refinement is active."""
    return _ENABLED


def status() -> dict:
    """Return current LLM configuration for observability endpoint."""
    return {
        "enabled": _ENABLED,
        "provider": _PROVIDER if _ENABLED else None,
        "model": _MODEL if _ENABLED else None,
        "base_url": _BASE_URL if _ENABLED else None,
        "timeout_sec": _TIMEOUT,
        "max_tokens": _MAX_TOKENS,
    }
