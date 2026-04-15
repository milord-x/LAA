"""
AgentDecision — structured output of the autonomous agent layer.

Every processed segment produces exactly one AgentDecision that carries
all routing flags and the explainable rationale behind each flag.
"""

from dataclasses import dataclass, field


@dataclass
class AgentDecision:
    """
    Represents the agent's autonomous decision about a single transcript segment.

    Flags drive downstream routing:
      - include_in_subtitles  → send to WebSocket / browser
      - include_in_avatar     → pass to sign-language synthesis
      - include_in_summary    → store in session transcript for summarisation
      - highlight_keywords    → annotate with extracted key terms
      - refresh_summary       → trigger an on-the-fly summary rebuild
      - is_relevant           → overall relevance verdict
      - is_noise              → segment is noise / hallucination / filler
      - is_duplicate          → segment repeats recent content
    """

    # --- Input ---
    input_text: str
    """Raw text coming out of ASR."""

    cleaned_text: str
    """Normalised text after stripping punctuation / extra whitespace."""

    # --- Verdicts ---
    is_relevant: bool = False
    """True when segment carries meaningful speech content."""

    is_noise: bool = False
    """True when segment is filler, hallucination, or non-speech artefact."""

    is_duplicate: bool = False
    """True when segment substantially repeats a recently accepted segment."""

    # --- Routing flags ---
    include_in_subtitles: bool = False
    """Send to the browser subtitle stream."""

    include_in_avatar: bool = False
    """Pass cleaned text to sign-language synthesis."""

    include_in_summary: bool = False
    """Append to session transcript for later summarisation."""

    highlight_keywords: bool = False
    """Attach keyword annotations to the subtitle payload."""

    refresh_summary: bool = False
    """Signal that a live summary update should be emitted now."""

    # --- Scoring ---
    importance_score: float = 0.0
    """
    Continuous relevance score in [0, 1].
    Drives refresh_summary threshold and future ranking.
    """

    word_count: int = 0
    """Number of meaningful (non-stopword) tokens."""

    # --- Explainability ---
    reason: str = ""
    """
    Human-readable rationale for the routing decision.
    Logged and can be surfaced in developer/debug UI.
    """

    reasons: list[str] = field(default_factory=list)
    """
    Individual rule traces that contributed to the final decision.
    Populated by AgentPolicy for full auditability.
    """
