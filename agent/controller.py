"""
AgentController — orchestration layer of the LAA autonomous agent.

Sits between ASR/processing output and the downstream sinks
(subtitles WebSocket, avatar synthesis, session transcript, summariser).

Responsibilities:
  1. Accept a raw transcript segment with metadata.
  2. Run AgentPolicy to produce an AgentDecision.
  3. Log every decision with its rationale (observability).
  4. Return the decision together with a normalised output payload
     ready for each sink.

This is the component that makes LAA an *autonomous* agent:
it independently decides what information reaches each output channel
without requiring manual per-chunk intervention from the operator.
"""

import logging
import time
from collections import deque
from typing import Optional

from agent.decision import AgentDecision
from agent.policy import AgentPolicy

logger = logging.getLogger("laa.agent")
logger.setLevel(logging.INFO)

if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("[Agent] %(levelname)s — %(message)s")
    )
    logger.addHandler(_handler)

_RECENT_REASONS_MAX = 20


class AgentController:
    """
    Autonomous decision controller for transcript segments.

    Usage in pipeline::

        decision = agent_controller.process(
            text=chunk.text,
            keywords=structured["keywords"],
        )
        if not decision.include_in_subtitles:
            return None
        payload = agent_controller.build_subtitle_payload(
            decision, synced_frame, timestamp
        )
    """

    def __init__(self) -> None:
        self._policy = AgentPolicy()

        # Counters — all reset on reset_session()
        self._total_accepted: int = 0
        self._total_rejected: int = 0
        self._duplicates_suppressed: int = 0
        self._avatar_allowed: int = 0
        self._summary_included: int = 0
        self._refresh_count: int = 0

        # Ring buffer of last N decision reasons for observability
        self._recent_reasons: deque[dict] = deque(maxlen=_RECENT_REASONS_MAX)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def process(
        self,
        text: str,
        keywords: Optional[list[str]] = None,
    ) -> AgentDecision:
        """
        Evaluate *text* and return a fully populated AgentDecision.

        Args:
            text:     Raw transcript segment from ASR.
            keywords: Pre-extracted keywords (from processing.structurer).

        Returns:
            AgentDecision with all routing flags set and reason populated.
        """
        t0 = time.monotonic()
        decision = self._policy.evaluate_segment(text, keywords=keywords or [])
        elapsed_ms = (time.monotonic() - t0) * 1000

        self._update_counters(decision)
        self._log_decision(decision, elapsed_ms)
        self._push_reason(decision, elapsed_ms)

        return decision

    # ------------------------------------------------------------------
    # Payload builder
    # ------------------------------------------------------------------

    def build_subtitle_payload(
        self,
        decision: AgentDecision,
        synced_frame,
        timestamp: float,
    ) -> dict:
        """
        Build the JSON payload sent to the browser WebSocket.

        Avatar fields are populated only when include_in_avatar is True.
        Attaches agent metadata block for frontend debug/styling.

        Args:
            decision:     AgentDecision produced by process().
            synced_frame: SyncedFrame from avatar.sync.sync_chunk(), or None.
            timestamp:    ASR start timestamp in seconds.
        """
        payload: dict = {
            "type": "subtitle",
            "text": decision.input_text,
            "keywords": [],
            "avatar_url": None,
            "avatar_sigml": None,
            "avatar_duration_ms": 0,
            "timestamp": timestamp,
            "agent": {
                "importance": decision.importance_score,
                "refresh_summary": decision.refresh_summary,
                "reason": decision.reason,
            },
        }

        if decision.include_in_avatar and synced_frame is not None:
            payload["avatar_url"] = synced_frame.avatar_url
            payload["avatar_sigml"] = synced_frame.avatar_sigml
            payload["avatar_duration_ms"] = synced_frame.duration_ms

        return payload

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def reset_session(self) -> None:
        """Reset all per-session state. Call when a new session starts."""
        self._policy.reset_session()
        self._total_accepted = 0
        self._total_rejected = 0
        self._duplicates_suppressed = 0
        self._avatar_allowed = 0
        self._summary_included = 0
        self._refresh_count = 0
        self._recent_reasons.clear()
        logger.info("session reset — all counters cleared")

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    @property
    def stats(self) -> dict:
        """Return full runtime statistics for /session/agent/stats endpoint."""
        total = self._total_accepted + self._total_rejected
        return {
            "accepted": self._total_accepted,
            "rejected": self._total_rejected,
            "total": total,
            "accept_rate": round(self._total_accepted / max(total, 1), 3),
            "duplicates_suppressed": self._duplicates_suppressed,
            "avatar_allowed": self._avatar_allowed,
            "summary_included": self._summary_included,
            "refresh_count": self._refresh_count,
            "word_budget": self._policy.word_budget,
            "recent_reasons": list(self._recent_reasons),
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _update_counters(self, decision: AgentDecision) -> None:
        if decision.is_noise or (not decision.is_relevant and not decision.is_duplicate):
            self._total_rejected += 1
        elif decision.is_duplicate:
            self._total_rejected += 1
            self._duplicates_suppressed += 1
        else:
            self._total_accepted += 1
            if decision.include_in_avatar:
                self._avatar_allowed += 1
            if decision.include_in_summary:
                self._summary_included += 1
            if decision.refresh_summary:
                self._refresh_count += 1

    def _log_decision(self, decision: AgentDecision, elapsed_ms: float) -> None:
        snippet = decision.input_text[:60].replace("\n", " ")

        if decision.is_noise:
            logger.info("REJECTED noise | %r | %s", snippet, decision.reason)
            return

        if decision.is_duplicate:
            logger.info("REJECTED duplicate | %r", snippet)
            return

        parts = [
            f"subtitle={'Y' if decision.include_in_subtitles else 'N'}",
            f"avatar={'Y' if decision.include_in_avatar else 'N'}",
            f"summary={'Y' if decision.include_in_summary else 'N'}",
            f"score={decision.importance_score:.2f}",
            f"refresh={'Y' if decision.refresh_summary else 'N'}",
            f"{elapsed_ms:.1f}ms",
        ]
        logger.info("ACCEPTED | %r | %s", snippet, " | ".join(parts))

        if decision.refresh_summary:
            logger.info("SUMMARY_REFRESH triggered")

    def _push_reason(self, decision: AgentDecision, elapsed_ms: float) -> None:
        entry = {
            "text": decision.input_text[:80],
            "verdict": (
                "noise" if decision.is_noise
                else "duplicate" if decision.is_duplicate
                else "accepted"
            ),
            "score": decision.importance_score,
            "reason": decision.reason,
            "ms": round(elapsed_ms, 1),
        }
        self._recent_reasons.append(entry)


# Module-level singleton — imported by pipeline
agent_controller = AgentController()
