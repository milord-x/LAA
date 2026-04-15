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
from typing import Optional

from agent.decision import AgentDecision
from agent.policy import AgentPolicy

logger = logging.getLogger("laa.agent")
logger.setLevel(logging.INFO)

# Ensure at least one handler when running outside uvicorn
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("[Agent] %(levelname)s — %(message)s")
    )
    logger.addHandler(_handler)


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
        # build output payload based on decision flags …
    """

    def __init__(self) -> None:
        self._policy = AgentPolicy()
        self._total_accepted: int = 0
        self._total_rejected: int = 0

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
                      Pass an empty list or None to let policy estimate.

        Returns:
            AgentDecision with all routing flags set and reason populated.
        """
        t0 = time.monotonic()
        decision = self._policy.evaluate_segment(text, keywords=keywords or [])
        elapsed_ms = (time.monotonic() - t0) * 1000

        self._log_decision(decision, elapsed_ms)
        return decision

    # ------------------------------------------------------------------
    # Payload builder
    # ------------------------------------------------------------------

    def build_subtitle_payload(
        self,
        decision: AgentDecision,
        synced_frame,           # avatar.sync.SyncedFrame
        timestamp: float,
    ) -> dict:
        """
        Build the JSON payload that is sent to the browser.

        Populates avatar fields only when include_in_avatar is True.
        Attaches importance metadata for potential frontend styling.

        Args:
            decision:     AgentDecision produced by process().
            synced_frame: SyncedFrame from avatar.sync.sync_chunk().
            timestamp:    ASR start timestamp (seconds).
        """
        payload: dict = {
            "type": "subtitle",
            "text": decision.input_text,
            "keywords": [] ,
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

        if decision.highlight_keywords and synced_frame is not None:
            # keywords come from structurer, not the frame; pass through
            pass  # caller attaches keywords from structured dict

        if decision.include_in_avatar and synced_frame is not None:
            payload["avatar_url"] = synced_frame.avatar_url
            payload["avatar_sigml"] = synced_frame.avatar_sigml
            payload["avatar_duration_ms"] = synced_frame.duration_ms

        return payload

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def reset_session(self) -> None:
        """Reset all per-session state.  Call when a new session starts."""
        self._policy.reset_session()
        logger.info("session reset — policy state cleared")

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    @property
    def stats(self) -> dict:
        """Return runtime statistics for health/debug endpoints."""
        total = self._total_accepted + self._total_rejected
        return {
            "accepted": self._total_accepted,
            "rejected": self._total_rejected,
            "total": total,
            "accept_rate": round(self._total_accepted / max(total, 1), 3),
            "word_budget": self._policy.word_budget,
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _log_decision(self, decision: AgentDecision, elapsed_ms: float) -> None:
        snippet = decision.input_text[:60].replace("\n", " ")

        if decision.is_noise:
            self._total_rejected += 1
            logger.info(
                "REJECTED noise=True | %r | %s",
                snippet,
                decision.reason,
            )
            return

        if decision.is_duplicate:
            self._total_rejected += 1
            logger.info(
                "REJECTED duplicate=True | %r",
                snippet,
            )
            return

        self._total_accepted += 1
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


# Module-level singleton — imported by pipeline
agent_controller = AgentController()
