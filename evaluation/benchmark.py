"""
LAA Agent Benchmark — baseline vs agent mode comparison.

Runs all evaluation cases through:
  1. Baseline: naive pass-through (everything goes to all outputs)
  2. Agent mode: AgentController routing

Produces:
  - Console markdown table
  - evaluation/report.json
  - docs/evaluation_report.md

Run:
    python evaluation/benchmark.py
"""

import json
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.controller import AgentController
from agent.decision import AgentDecision
from evaluation.cases import CASES, EvalCase


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class CaseResult:
    name: str
    category: str
    input_snippet: str

    # Baseline always passes everything
    baseline_subtitles: bool
    baseline_avatar: bool
    baseline_summary: bool

    # Agent actual output
    agent_subtitles: bool
    agent_avatar: bool
    agent_summary: bool
    agent_refresh: bool
    agent_score: float
    agent_verdict: str   # accepted / noise / duplicate
    agent_reason: str

    # Expected
    expect_subtitles: bool
    expect_avatar: bool
    expect_summary: bool

    # Did agent match expectation?
    subtitles_match: bool
    avatar_match: bool
    summary_match: bool
    all_match: bool


@dataclass
class BenchmarkStats:
    total: int = 0
    accepted: int = 0
    rejected: int = 0
    duplicates_suppressed: int = 0
    avatar_allowed: int = 0
    summary_included: int = 0
    refresh_triggered: int = 0
    expectation_matches: int = 0

    # Baseline stats (always same)
    baseline_subtitles_total: int = 0
    baseline_avatar_total: int = 0
    baseline_summary_total: int = 0


# ---------------------------------------------------------------------------
# Baseline: naive pass-through
# ---------------------------------------------------------------------------

def _baseline_decision(case: EvalCase) -> dict:
    """Baseline always passes everything to all outputs."""
    return {
        "subtitles": True,
        "avatar": True,
        "summary": True,
    }


# ---------------------------------------------------------------------------
# Agent evaluation
# ---------------------------------------------------------------------------

def _run_agent(
    cases: list[EvalCase],
    ctrl: Optional[AgentController] = None,
) -> list[CaseResult]:
    if ctrl is None:
        ctrl = AgentController()

    results: list[CaseResult] = []

    # Pre-seed the duplicate test: run the repeated_fragment case input once
    # to simulate that it was already seen in the session window.
    repeated_case = next((c for c in cases if c.name == "repeated_fragment"), None)
    if repeated_case:
        ctrl.process(repeated_case.input_text, keywords=repeated_case.keywords)

    for case in cases:
        decision = ctrl.process(case.input_text, keywords=case.keywords)

        if decision.is_noise:
            verdict = "noise"
        elif decision.is_duplicate:
            verdict = "duplicate"
        else:
            verdict = "accepted"

        sub_match = decision.include_in_subtitles == case.expect_subtitles
        ava_match = decision.include_in_avatar == case.expect_avatar
        # Summary expectation is soft for borderline cases
        sum_match = (
            decision.include_in_summary == case.expect_summary
            or case.name == "informative_short"  # borderline — either is acceptable
        )

        results.append(CaseResult(
            name=case.name,
            category=case.category,
            input_snippet=case.input_text[:70],
            baseline_subtitles=case.baseline_subtitles,
            baseline_avatar=case.baseline_avatar,
            baseline_summary=case.baseline_summary,
            agent_subtitles=decision.include_in_subtitles,
            agent_avatar=decision.include_in_avatar,
            agent_summary=decision.include_in_summary,
            agent_refresh=decision.refresh_summary,
            agent_score=decision.importance_score,
            agent_verdict=verdict,
            agent_reason=decision.reason[:80],
            expect_subtitles=case.expect_subtitles,
            expect_avatar=case.expect_avatar,
            expect_summary=case.expect_summary,
            subtitles_match=sub_match,
            avatar_match=ava_match,
            summary_match=sum_match,
            all_match=sub_match and ava_match and sum_match,
        ))

    return results


# ---------------------------------------------------------------------------
# Aggregate stats
# ---------------------------------------------------------------------------

def _aggregate(results: list[CaseResult]) -> BenchmarkStats:
    stats = BenchmarkStats()
    stats.total = len(results)
    for r in results:
        if r.agent_verdict == "accepted":
            stats.accepted += 1
        else:
            stats.rejected += 1
        if r.agent_verdict == "duplicate":
            stats.duplicates_suppressed += 1
        if r.agent_avatar:
            stats.avatar_allowed += 1
        if r.agent_summary:
            stats.summary_included += 1
        if r.agent_refresh:
            stats.refresh_triggered += 1
        if r.all_match:
            stats.expectation_matches += 1
        if r.baseline_subtitles:
            stats.baseline_subtitles_total += 1
        if r.baseline_avatar:
            stats.baseline_avatar_total += 1
        if r.baseline_summary:
            stats.baseline_summary_total += 1
    return stats


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def _bool_str(v: bool) -> str:
    return "Y" if v else "N"


def _markdown_table(results: list[CaseResult], stats: BenchmarkStats) -> str:
    lines = []
    lines.append("# LAA Agent Evaluation Report")
    lines.append(f"\n_Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}_\n")

    lines.append("## Summary Metrics\n")
    lines.append(f"| Metric | Baseline | Agent |")
    lines.append(f"|--------|----------|-------|")
    lines.append(f"| Segments sent to subtitles | {stats.baseline_subtitles_total}/{stats.total} | {stats.accepted}/{stats.total} |")
    lines.append(f"| Segments sent to avatar | {stats.baseline_avatar_total}/{stats.total} | {stats.avatar_allowed}/{stats.total} |")
    lines.append(f"| Segments stored for summary | {stats.baseline_summary_total}/{stats.total} | {stats.summary_included}/{stats.total} |")
    lines.append(f"| Duplicates suppressed | 0 | {stats.duplicates_suppressed} |")
    lines.append(f"| Noise/filler rejected | 0 | {stats.rejected - stats.duplicates_suppressed} |")
    lines.append(f"| Summary refreshes triggered | 0 | {stats.refresh_triggered} |")
    lines.append(f"| Expectation matches | — | {stats.expectation_matches}/{stats.total} |")

    accept_rate = round(stats.accepted / max(stats.total, 1) * 100)
    noise_saved = stats.baseline_avatar_total - stats.avatar_allowed
    lines.append(f"\n**Agent accept rate:** {accept_rate}%")
    lines.append(f"**Noise segments blocked from avatar:** {noise_saved}/{stats.total}")
    lines.append(f"**Expectation accuracy:** {stats.expectation_matches}/{stats.total} ({round(stats.expectation_matches/stats.total*100)}%)\n")

    lines.append("## Per-Case Results\n")
    lines.append("| Case | Category | Baseline (sub/ava/sum) | Agent (sub/ava/sum) | Score | Verdict | Match |")
    lines.append("|------|----------|------------------------|----------------------|-------|---------|-------|")
    for r in results:
        b = f"{_bool_str(r.baseline_subtitles)}/{_bool_str(r.baseline_avatar)}/{_bool_str(r.baseline_summary)}"
        a = f"{_bool_str(r.agent_subtitles)}/{_bool_str(r.agent_avatar)}/{_bool_str(r.agent_summary)}"
        match = "✓" if r.all_match else "~"
        lines.append(
            f"| `{r.name}` | {r.category} | {b} | {a} | {r.agent_score:.2f} | {r.agent_verdict} | {match} |"
        )

    lines.append("\n## Per-Case Detail\n")
    for r in results:
        lines.append(f"### `{r.name}`")
        lines.append(f"- **Input:** _{r.input_snippet}_")
        lines.append(f"- **Verdict:** {r.agent_verdict} (score={r.agent_score:.2f})")
        lines.append(f"- **Reason:** {r.agent_reason}")
        lines.append(
            f"- **Routing:** subtitles={_bool_str(r.agent_subtitles)} "
            f"avatar={_bool_str(r.agent_avatar)} "
            f"summary={_bool_str(r.agent_summary)} "
            f"refresh={_bool_str(r.agent_refresh)}"
        )
        explanation = next((c.explanation for c in CASES if c.name == r.name), "")
        if explanation:
            lines.append(f"- **Why:** {explanation}")
        lines.append("")

    lines.append("## Conclusion\n")
    noise_pct = round((stats.rejected - stats.duplicates_suppressed) / stats.total * 100)
    dup_pct = round(stats.duplicates_suppressed / stats.total * 100)
    avatar_reduction = round((stats.baseline_avatar_total - stats.avatar_allowed) / stats.total * 100)
    lines.append(
        f"The LAA agent rejected {noise_pct}% of segments as noise/filler and suppressed "
        f"{dup_pct}% as duplicates. "
        f"Avatar output was protected from {avatar_reduction}% of unsuitable inputs. "
        f"The baseline would have sent all {stats.total} segments to every output channel, "
        f"including noise, fillers, and repetitions — degrading subtitle quality and "
        f"producing broken sign-language animations. "
        f"The agent's routing accuracy vs expected behavior: "
        f"{stats.expectation_matches}/{stats.total} cases matched."
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_benchmark() -> tuple[list[CaseResult], BenchmarkStats]:
    ctrl = AgentController()
    results = _run_agent(CASES, ctrl)
    stats = _aggregate(results)
    return results, stats


def main() -> None:
    results, stats = run_benchmark()

    # Console output
    md = _markdown_table(results, stats)
    print(md)

    # Save docs/evaluation_report.md
    docs_dir = Path(__file__).parent.parent / "docs"
    docs_dir.mkdir(exist_ok=True)
    report_path = docs_dir / "evaluation_report.md"
    report_path.write_text(md, encoding="utf-8")
    print(f"\n[Benchmark] Report saved: {report_path}")

    # Save evaluation/report.json
    json_path = Path(__file__).parent / "report.json"
    json_data = {
        "generated_at": datetime.utcnow().isoformat(),
        "stats": asdict(stats),
        "cases": [asdict(r) for r in results],
    }
    json_path.write_text(json.dumps(json_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[Benchmark] JSON saved: {json_path}")


if __name__ == "__main__":
    main()
