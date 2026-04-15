"""
AgentPolicy — rule-based scoring engine.

Applies explicit, explainable rules to decide how a transcript segment
should be routed.  No external LLM calls are required at this layer;
the policy works offline and deterministically.

Design principle: every decision has a traceable rule source so the
system can be described as an explainable autonomous agent.
"""

import re
from typing import Optional

from agent.decision import AgentDecision

# ---------------------------------------------------------------------------
# Thresholds (tune per deployment)
# ---------------------------------------------------------------------------

MIN_WORDS = 2
"""Segments with fewer meaningful words are discarded."""

MIN_CHARS = 8
"""Absolute minimum character count after cleaning."""

DUPLICATE_OVERLAP_RATIO = 0.75
"""If >75% of the new segment appears verbatim in the recent window, suppress."""

KEYWORD_DENSITY_HIGH = 0.25
"""keyword_count / word_count above this → 'important' segment."""

IMPORTANCE_THRESHOLD_SUMMARY = 0.40
"""Importance score above this → include in summary."""

IMPORTANCE_THRESHOLD_AVATAR = 0.30
"""Importance score above this → send to avatar."""

SUMMARY_REFRESH_WORD_BUDGET = 80
"""Trigger a live summary refresh after this many accepted words in a session."""

LONG_SEGMENT_WORDS = 20
"""Segments longer than this are always included in summary."""

# ---------------------------------------------------------------------------
# Stopwords (Russian + English, minimal set)
# ---------------------------------------------------------------------------

_STOPWORDS: set[str] = {
    "и", "в", "на", "с", "по", "из", "для", "это", "что", "как",
    "но", "а", "же", "от", "к", "или", "не", "то", "так", "при",
    "он", "она", "они", "мы", "вы", "я", "его", "её", "их", "был",
    "было", "быть", "вот", "тут", "там", "уже", "ещё", "очень",
    "the", "a", "an", "is", "are", "was", "were", "of", "in", "to",
    "and", "or", "but", "it", "this", "that", "with", "for",
}

# ---------------------------------------------------------------------------
# Filler / noise patterns
# ---------------------------------------------------------------------------

_FILLER_EXACT: set[str] = {
    "да", "нет", "ок", "окей", "хорошо", "ладно", "понятно",
    "yes", "no", "ok", "okay", "hmm", "uh", "um", "ah", "eh",
    "угу", "ага", "эм", "эээ", "ну",
}

_FILLER_PATTERNS: list[re.Pattern] = [
    re.compile(r"^[эа-я]{1,3}[\.…,]*$", re.I),   # "эм", "ааа", "ну"
    re.compile(r"^[a-z]{1,3}[\.…,]*$", re.I),     # "um", "uh", "ah"
]


# ---------------------------------------------------------------------------
# Policy engine
# ---------------------------------------------------------------------------

class AgentPolicy:
    """
    Stateful policy engine.  Holds a small window of recent accepted
    segments to enable duplicate suppression across consecutive chunks.
    """

    def __init__(self, recent_window: int = 5) -> None:
        self._recent: list[str] = []
        """Ring buffer of recently accepted cleaned texts."""
        self._recent_window = recent_window
        self._accepted_word_budget: int = 0
        """Running count of accepted words — drives summary refresh trigger."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate_segment(
        self,
        text: str,
        keywords: Optional[list[str]] = None,
    ) -> AgentDecision:
        """
        Main entry point.  Evaluates *text* and returns a fully populated
        AgentDecision with all routing flags and an explainable rationale.

        Args:
            text:     Raw ASR output for this segment.
            keywords: Pre-extracted keywords (from processing.structurer).
                      If None, policy derives its own keyword count estimate.
        """
        decision = AgentDecision(
            input_text=text,
            cleaned_text=self._clean(text),
        )

        traces: list[str] = []

        # ----------------------------------------------------------------
        # Stage 1 — hard-reject gates (noise / trivial / filler)
        # ----------------------------------------------------------------

        if self._is_empty(decision.cleaned_text):
            decision.is_noise = True
            decision.reason = "empty or near-empty segment"
            decision.reasons = ["EMPTY_SEGMENT"]
            return decision

        if self._is_filler(decision.cleaned_text):
            decision.is_noise = True
            decision.reason = "filler word / non-speech artefact"
            decision.reasons = ["FILLER_WORD"]
            return decision

        word_count = self._count_meaningful_words(decision.cleaned_text)
        decision.word_count = word_count

        if word_count < MIN_WORDS:
            decision.is_noise = True
            decision.reason = f"too few meaningful words ({word_count} < {MIN_WORDS})"
            decision.reasons = ["TOO_SHORT"]
            return decision

        # ----------------------------------------------------------------
        # Stage 2 — duplicate suppression
        # ----------------------------------------------------------------

        if self._is_duplicate(decision.cleaned_text):
            decision.is_duplicate = True
            decision.reason = "segment substantially repeats recent content"
            decision.reasons = ["DUPLICATE_SUPPRESSED"]
            return decision

        # ----------------------------------------------------------------
        # Stage 3 — importance scoring
        # ----------------------------------------------------------------

        score = self._compute_importance(
            cleaned=decision.cleaned_text,
            word_count=word_count,
            keywords=keywords or [],
        )
        decision.importance_score = score
        traces.append(f"importance_score={score:.2f}")

        # ----------------------------------------------------------------
        # Stage 4 — routing decisions
        # ----------------------------------------------------------------

        decision.is_relevant = True

        # Subtitles: every relevant, non-duplicate segment
        decision.include_in_subtitles = True
        traces.append("SUBTITLES_YES")

        # Keywords: above density threshold or explicitly provided
        kw_density = len(keywords or []) / max(word_count, 1)
        if kw_density >= KEYWORD_DENSITY_HIGH or score >= 0.5:
            decision.highlight_keywords = True
            traces.append("KEYWORDS_HIGHLIGHTED")

        # Avatar: clean, non-fragmented, above avatar threshold
        decision.include_in_avatar = self.should_send_to_avatar(
            score, word_count, decision.cleaned_text
        )
        if decision.include_in_avatar:
            traces.append("AVATAR_YES")
        else:
            traces.append("AVATAR_SKIPPED(score_too_low_or_fragmented)")

        # Summary: long segments always in, short only if important
        decision.include_in_summary = self.should_include_in_summary(
            score, word_count
        )
        if decision.include_in_summary:
            traces.append("SUMMARY_YES")
            self._accepted_word_budget += word_count
        else:
            traces.append("SUMMARY_SKIPPED")

        # Summary refresh: budget exceeded
        decision.refresh_summary = self.should_refresh_summary()
        if decision.refresh_summary:
            traces.append("SUMMARY_REFRESH_TRIGGERED")
            self._accepted_word_budget = 0  # reset budget

        # ----------------------------------------------------------------
        # Finalise
        # ----------------------------------------------------------------

        decision.reasons = traces
        decision.reason = "; ".join(traces)

        # Accept into recent window only after all routing decided
        self._push_recent(decision.cleaned_text)

        return decision

    def should_include_in_summary(self, score: float, word_count: int) -> bool:
        """
        Return True when a segment should be stored for summarisation.

        Rule: long segments always in; short segments only if important enough.
        """
        if word_count >= LONG_SEGMENT_WORDS:
            return True
        return score >= IMPORTANCE_THRESHOLD_SUMMARY

    def should_send_to_avatar(
        self, score: float, word_count: int, cleaned_text: str
    ) -> bool:
        """
        Return True when cleaned text should be forwarded to sign-language synthesis.

        Rejects: fragmented text (< 3 words), low-score noise, very long segments
        that would produce unwatchable sign output.
        """
        if word_count < 3:
            return False
        if score < IMPORTANCE_THRESHOLD_AVATAR:
            return False
        # Reject excessively long segments (sign animation would desync)
        if word_count > 40:
            return False
        return True

    def should_refresh_summary(self) -> bool:
        """Return True when the accumulated word budget warrants a live summary update."""
        return self._accepted_word_budget >= SUMMARY_REFRESH_WORD_BUDGET

    def reset_session(self) -> None:
        """Call at session start/end to clear inter-session state."""
        self._recent.clear()
        self._accepted_word_budget = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clean(text: str) -> str:
        """Strip punctuation, normalise whitespace."""
        t = text.strip()
        t = re.sub(r"[.,!?;:…\-–—\[\]()\"\']", " ", t)
        t = re.sub(r"\s{2,}", " ", t).strip()
        return t

    @staticmethod
    def _is_empty(text: str) -> bool:
        return len(text.strip()) < MIN_CHARS

    @staticmethod
    def _is_filler(text: str) -> bool:
        lower = text.strip().lower()
        if lower in _FILLER_EXACT:
            return True
        for pattern in _FILLER_PATTERNS:
            if pattern.fullmatch(lower):
                return True
        return False

    @staticmethod
    def _count_meaningful_words(text: str) -> int:
        words = re.findall(r"\b[а-яёА-ЯЁa-zA-Z]{2,}\b", text.lower())
        return sum(1 for w in words if w not in _STOPWORDS)

    def _is_duplicate(self, cleaned: str) -> bool:
        """
        Compare against recent accepted segments using substring overlap ratio.
        """
        lower = cleaned.lower()
        for recent in self._recent:
            overlap = self._overlap_ratio(lower, recent.lower())
            if overlap >= DUPLICATE_OVERLAP_RATIO:
                return True
        return False

    @staticmethod
    def _overlap_ratio(a: str, b: str) -> float:
        """
        Fraction of the shorter string's words that appear in the longer string.
        """
        words_a = set(re.findall(r"\b\w+\b", a))
        words_b = set(re.findall(r"\b\w+\b", b))
        if not words_a or not words_b:
            return 0.0
        shorter = words_a if len(words_a) <= len(words_b) else words_b
        longer = words_b if len(words_a) <= len(words_b) else words_a
        if not shorter:
            return 0.0
        return len(shorter & longer) / len(shorter)

    def _push_recent(self, text: str) -> None:
        self._recent.append(text)
        if len(self._recent) > self._recent_window:
            self._recent.pop(0)

    def _compute_importance(
        self,
        cleaned: str,
        word_count: int,
        keywords: list[str],
    ) -> float:
        """
        Composite importance score in [0, 1].

        Components:
          - length bonus:    longer segments carry more information
          - keyword density: ratio of keyword hits to total words
          - sentence bonus:  segment ends with proper punctuation (complete thought)
        """
        if word_count == 0:
            return 0.0

        # Length component (saturates at LONG_SEGMENT_WORDS)
        length_score = min(word_count / LONG_SEGMENT_WORDS, 1.0)

        # Keyword density component
        kw_hits = sum(
            1 for kw in keywords
            if kw.lower() in cleaned.lower()
        )
        kw_score = min(kw_hits / max(word_count, 1) / KEYWORD_DENSITY_HIGH, 1.0)

        # Sentence completeness bonus (ends with . ! ?)
        sentence_bonus = 0.15 if re.search(r"[.!?]\s*$", self.input_text if hasattr(self, "input_text") else cleaned) else 0.0

        score = 0.5 * length_score + 0.35 * kw_score + 0.15 * sentence_bonus
        return round(min(score, 1.0), 4)

    # Expose for debugging
    @property
    def recent_window(self) -> list[str]:
        return list(self._recent)

    @property
    def word_budget(self) -> int:
        return self._accepted_word_budget
