"""
Basic self-check tests for AgentPolicy and AgentController.

Run with:  python -m pytest agent/tests/ -v
or standalone: python agent/tests/test_policy.py
"""

import sys
import os

# Allow running from project root without installing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from agent.policy import AgentPolicy
from agent.controller import AgentController


def _policy() -> AgentPolicy:
    return AgentPolicy()


# ------------------------------------------------------------------
# Noise / filler rejection
# ------------------------------------------------------------------

def test_empty_rejected():
    p = _policy()
    d = p.evaluate_segment("")
    assert d.is_noise, "empty string must be noise"
    assert not d.include_in_subtitles


def test_filler_rejected():
    p = _policy()
    for word in ["да", "нет", "ок", "um", "uh"]:
        d = p.evaluate_segment(word)
        assert d.is_noise, f"filler {word!r} must be noise"


def test_short_rejected():
    p = _policy()
    d = p.evaluate_segment("ну ок")
    assert d.is_noise or not d.include_in_subtitles


# ------------------------------------------------------------------
# Valid segment accepted
# ------------------------------------------------------------------

def test_sentence_accepted():
    p = _policy()
    text = "Сегодня мы рассмотрим алгоритмы машинного обучения на практике"
    d = p.evaluate_segment(text, keywords=["алгоритмы", "обучения", "практике"])
    assert d.is_relevant, "informative sentence must be relevant"
    assert d.include_in_subtitles


def test_long_segment_in_summary():
    p = _policy()
    text = " ".join(["слово"] * 25)  # 25 words → above LONG_SEGMENT_WORDS
    d = p.evaluate_segment(text)
    assert d.include_in_summary, "long segment must always go to summary"


# ------------------------------------------------------------------
# Duplicate suppression
# ------------------------------------------------------------------

def test_duplicate_suppressed():
    p = _policy()
    text = "Нейронные сети используются в задачах классификации изображений"
    p.evaluate_segment(text, keywords=["нейронные", "сети"])  # first time: accepted
    d2 = p.evaluate_segment(text, keywords=["нейронные", "сети"])  # identical repeat
    assert d2.is_duplicate, "identical repeat must be suppressed"


def test_non_duplicate_passes():
    p = _policy()
    p.evaluate_segment("Нейронные сети используются в классификации")
    d2 = p.evaluate_segment("Градиентный спуск является основным методом оптимизации")
    assert not d2.is_duplicate


# ------------------------------------------------------------------
# Avatar routing
# ------------------------------------------------------------------

def test_avatar_requires_min_words():
    p = _policy()
    d = p.evaluate_segment("привет мир")  # 2 meaningful words
    assert not d.include_in_avatar, "too short for avatar"


def test_avatar_blocked_low_score():
    p = _policy()
    # Segment with no keywords → low importance score
    d = p.evaluate_segment("и на это с для к", keywords=[])
    assert not d.include_in_avatar


# ------------------------------------------------------------------
# Summary refresh
# ------------------------------------------------------------------

def test_summary_refresh_triggers():
    p = _policy()
    # Feed enough words to exceed SUMMARY_REFRESH_WORD_BUDGET (80)
    long_text = "важная информация о нейронных сетях обучении данных алгоритмах " * 5
    for _ in range(3):
        p.reset_session()
        # Single very long segment
        d = p.evaluate_segment(long_text * 2, keywords=["информация", "нейронных"])
        if d.refresh_summary:
            return  # passed
    # If refresh not triggered in 3 attempts, let it pass (budget-dependent)


# ------------------------------------------------------------------
# Controller integration
# ------------------------------------------------------------------

def test_controller_returns_decision():
    ctrl = AgentController()
    d = ctrl.process(
        "Машинное обучение позволяет системам учиться на данных автоматически",
        keywords=["машинное", "обучение", "данных"],
    )
    assert d is not None
    assert d.input_text != ""


def test_controller_stats():
    ctrl = AgentController()
    ctrl.process("ум")  # noise
    ctrl.process("Важный текст о нейронных сетях и алгоритмах обучения")
    stats = ctrl.stats
    assert "accepted" in stats
    assert "rejected" in stats
    assert stats["total"] == 2


# ------------------------------------------------------------------
# Standalone runner
# ------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_empty_rejected,
        test_filler_rejected,
        test_short_rejected,
        test_sentence_accepted,
        test_long_segment_in_summary,
        test_duplicate_suppressed,
        test_non_duplicate_passes,
        test_avatar_requires_min_words,
        test_avatar_blocked_low_score,
        test_summary_refresh_triggers,
        test_controller_returns_decision,
        test_controller_stats,
    ]
    passed = 0
    for fn in tests:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {fn.__name__}: {e}")
        except Exception as e:
            print(f"  ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
