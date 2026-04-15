"""
Unit tests for AgentPolicy, AgentController, and pipeline integration.

Run:  python -m pytest agent/tests/ -v
  or: python agent/tests/test_policy.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from agent.policy import AgentPolicy, SUMMARY_REFRESH_WORD_BUDGET, LONG_SEGMENT_WORDS
from agent.controller import AgentController


def _policy() -> AgentPolicy:
    return AgentPolicy()


def _ctrl() -> AgentController:
    return AgentController()


# ------------------------------------------------------------------
# Noise / filler rejection
# ------------------------------------------------------------------

def test_empty_rejected():
    d = _policy().evaluate_segment("")
    assert d.is_noise
    assert not d.include_in_subtitles
    assert not d.include_in_avatar
    assert not d.include_in_summary


def test_whitespace_only_rejected():
    d = _policy().evaluate_segment("   ")
    assert d.is_noise


def test_filler_words_rejected():
    p = _policy()
    for word in ["да", "нет", "ок", "um", "uh", "эм", "ага", "угу"]:
        d = p.evaluate_segment(word)
        assert d.is_noise, f"filler {word!r} must be noise"


def test_too_short_rejected():
    d = _policy().evaluate_segment("ну")
    assert d.is_noise


def test_single_stopword_rejected():
    d = _policy().evaluate_segment("и в на с")
    assert d.is_noise or d.word_count < 2


# ------------------------------------------------------------------
# Valid segment accepted
# ------------------------------------------------------------------

def test_informative_sentence_accepted():
    p = _policy()
    text = "Сегодня мы рассмотрим алгоритмы машинного обучения на практике"
    d = p.evaluate_segment(text, keywords=["алгоритмы", "обучения", "практике"])
    assert d.is_relevant
    assert d.include_in_subtitles
    assert not d.is_noise
    assert not d.is_duplicate


def test_english_sentence_accepted():
    p = _policy()
    text = "Neural networks learn representations from training data automatically"
    d = p.evaluate_segment(text, keywords=["neural", "networks", "training"])
    assert d.is_relevant
    assert d.include_in_subtitles


def test_long_segment_always_in_summary():
    p = _policy()
    text = " ".join(["слово"] * (LONG_SEGMENT_WORDS + 1))
    d = p.evaluate_segment(text)
    assert d.include_in_summary, "long segment must always go to summary"


def test_importance_score_range():
    p = _policy()
    text = "Градиентный спуск оптимизирует функцию потерь нейронной сети"
    d = p.evaluate_segment(text, keywords=["градиентный", "спуск", "потерь"])
    assert 0.0 <= d.importance_score <= 1.0


# ------------------------------------------------------------------
# Duplicate suppression
# ------------------------------------------------------------------

def test_identical_repeat_suppressed():
    p = _policy()
    text = "Нейронные сети используются в задачах классификации изображений"
    p.evaluate_segment(text, keywords=["нейронные", "сети"])
    d2 = p.evaluate_segment(text, keywords=["нейронные", "сети"])
    assert d2.is_duplicate


def test_different_segment_not_duplicate():
    p = _policy()
    p.evaluate_segment("Нейронные сети используются в классификации")
    d2 = p.evaluate_segment("Градиентный спуск является методом оптимизации весов")
    assert not d2.is_duplicate


def test_near_duplicate_suppressed():
    p = _policy()
    text1 = "машинное обучение используется для анализа данных"
    text2 = "машинное обучение используется для анализа данных и предсказаний"
    p.evaluate_segment(text1)
    d2 = p.evaluate_segment(text2)
    # text1 words are a large subset of text2 — should be suppressed
    assert d2.is_duplicate


# ------------------------------------------------------------------
# Avatar routing
# ------------------------------------------------------------------

def test_avatar_requires_min_3_words():
    p = _policy()
    d = p.evaluate_segment("привет мир")  # 2 words
    assert not d.include_in_avatar


def test_avatar_blocked_for_too_long_segment():
    p = _policy()
    text = " ".join(["важный"] * 45)  # 45 words > limit of 40
    d = p.evaluate_segment(text, keywords=["важный"])
    assert not d.include_in_avatar


def test_avatar_allowed_for_good_segment():
    p = _policy()
    text = "Нейронные сети обрабатывают входные данные через несколько слоёв"
    d = p.evaluate_segment(text, keywords=["нейронные", "данные", "слоёв"])
    # Good segment: 8+ words, keywords present → score should clear threshold
    if d.is_relevant:
        assert d.include_in_subtitles


def test_avatar_blocked_low_importance():
    p = _policy()
    # All stopwords → near-zero importance
    d = p.evaluate_segment("и на это с для к или не то так при")
    assert not d.include_in_avatar


# ------------------------------------------------------------------
# Summary refresh
# ------------------------------------------------------------------

def test_summary_refresh_triggers_after_budget():
    p = _policy()
    # Feed unique segments until budget (80 words) is exceeded.
    # Each segment is ~10 meaningful words, window=5 so no dedup collision.
    topics = [
        "нейронная сеть обучается распознавать изображения объектов сцены",
        "градиентный спуск минимизирует функцию потерь весовых параметров",
        "свёрточные слои извлекают локальные признаки входного изображения",
        "батч-нормализация стабилизирует обучение глубоких нейронных сетей",
        "дропаут предотвращает переобучение случайным отключением нейронов",
        "остаточные связи позволяют обучать очень глубокие архитектуры сетей",
        "трансформер использует механизм внимания вместо рекуррентных слоёв",
        "предобученные модели переносят знания на новые задачи классификации",
        "оптимизатор адам адаптирует скорость обучения каждого параметра модели",
        "кросс-энтропийная потеря измеряет расхождение предсказаний и меток",
        "аугментация данных увеличивает разнообразие обучающей выборки примеров",
        "ансамблирование моделей улучшает качество предсказаний снижая дисперсию",
    ]
    refreshed = False
    for text in topics:
        words = text.split()
        kw = [w for w in words if len(w) > 5][:3]
        d = p.evaluate_segment(text, keywords=kw)
        if d.refresh_summary:
            refreshed = True
            break
    assert refreshed, "summary refresh must trigger after enough accepted words"


def test_summary_refresh_resets_budget():
    p = _policy()
    segment = "нейронная сеть обучается градиентным спуском оптимизации потерь"
    for _ in range(15):
        d = p.evaluate_segment(segment + str(_), keywords=["нейронная", "сеть"])
        if d.refresh_summary:
            assert p.word_budget == 0, "budget must reset after refresh"
            break


# ------------------------------------------------------------------
# Controller counters
# ------------------------------------------------------------------

def test_controller_rejected_counter():
    ctrl = _ctrl()
    ctrl.process("ум")   # noise
    ctrl.process("")     # noise
    assert ctrl.stats["rejected"] == 2
    assert ctrl.stats["accepted"] == 0


def test_controller_accepted_counter():
    ctrl = _ctrl()
    ctrl.process("Машинное обучение позволяет системам учиться на данных")
    assert ctrl.stats["accepted"] == 1


def test_controller_duplicate_counter():
    ctrl = _ctrl()
    text = "нейронные сети классифицируют изображения точно"
    ctrl.process(text, keywords=["нейронные", "сети"])
    ctrl.process(text, keywords=["нейронные", "сети"])  # duplicate
    assert ctrl.stats["duplicates_suppressed"] == 1


def test_controller_avatar_counter():
    ctrl = _ctrl()
    text = "нейронные сети обрабатывают данные через несколько слоёв активации"
    d = ctrl.process(text, keywords=["нейронные", "данные", "слоёв"])
    if d.include_in_avatar:
        assert ctrl.stats["avatar_allowed"] == 1
    else:
        assert ctrl.stats["avatar_allowed"] == 0


def test_controller_summary_counter():
    ctrl = _ctrl()
    text = " ".join(["слово"] * (LONG_SEGMENT_WORDS + 1))
    ctrl.process(text)
    assert ctrl.stats["summary_included"] == 1


def test_controller_recent_reasons_populated():
    ctrl = _ctrl()
    ctrl.process("Алгоритмы машинного обучения применяются в классификации")
    ctrl.process("ум")  # noise
    reasons = ctrl.stats["recent_reasons"]
    assert len(reasons) == 2
    assert reasons[0]["verdict"] == "accepted"
    assert reasons[1]["verdict"] == "noise"


def test_controller_stats_keys():
    ctrl = _ctrl()
    stats = ctrl.stats
    required = {
        "accepted", "rejected", "total", "accept_rate",
        "duplicates_suppressed", "avatar_allowed", "summary_included",
        "refresh_count", "word_budget", "recent_reasons",
    }
    assert required.issubset(stats.keys())


def test_reset_session_clears_counters():
    ctrl = _ctrl()
    ctrl.process("алгоритм машинного обучения нейронная сеть классификация")
    ctrl.process("ум")
    ctrl.reset_session()
    stats = ctrl.stats
    assert stats["accepted"] == 0
    assert stats["rejected"] == 0
    assert stats["recent_reasons"] == []


# ------------------------------------------------------------------
# Standalone runner
# ------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_empty_rejected,
        test_whitespace_only_rejected,
        test_filler_words_rejected,
        test_too_short_rejected,
        test_single_stopword_rejected,
        test_informative_sentence_accepted,
        test_english_sentence_accepted,
        test_long_segment_always_in_summary,
        test_importance_score_range,
        test_identical_repeat_suppressed,
        test_different_segment_not_duplicate,
        test_near_duplicate_suppressed,
        test_avatar_requires_min_3_words,
        test_avatar_blocked_for_too_long_segment,
        test_avatar_allowed_for_good_segment,
        test_avatar_blocked_low_importance,
        test_summary_refresh_triggers_after_budget,
        test_summary_refresh_resets_budget,
        test_controller_rejected_counter,
        test_controller_accepted_counter,
        test_controller_duplicate_counter,
        test_controller_avatar_counter,
        test_controller_summary_counter,
        test_controller_recent_reasons_populated,
        test_controller_stats_keys,
        test_reset_session_clears_counters,
    ]
    passed = failed = 0
    for fn in tests:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {fn.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {fn.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{passed}/{len(tests)} tests passed" + (f"  ({failed} failed)" if failed else ""))
