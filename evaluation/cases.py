"""
Test cases for LAA agent evaluation.

Each case defines an input segment, the expected agent routing decision,
and a short explanation of why the expected behavior is correct.

Used by benchmark.py to validate agent behavior and produce
quantitative comparison between baseline and agent mode.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EvalCase:
    """A single evaluation case."""

    name: str
    """Short identifier for reporting."""

    input_text: str
    """Raw ASR-like input segment."""

    keywords: list[str]
    """Keywords that would be extracted by processing.structurer."""

    # Expected routing
    expect_subtitles: bool
    expect_avatar: bool
    expect_summary: bool
    expect_refresh: bool = False

    # What baseline (naive pass-through) would do
    baseline_subtitles: bool = True
    baseline_avatar: bool = True
    baseline_summary: bool = True

    category: str = "general"
    """Category label for grouping in report."""

    explanation: str = ""
    """Why the expected routing is correct."""


CASES: list[EvalCase] = [
    EvalCase(
        name="noisy_fragment",
        input_text="эм ааа ну",
        keywords=[],
        expect_subtitles=False,
        expect_avatar=False,
        expect_summary=False,
        baseline_subtitles=True,
        baseline_avatar=True,
        baseline_summary=True,
        category="noise",
        explanation=(
            "Pure noise/filler. Agent must reject entirely. "
            "Baseline would pass it to all outputs, polluting subtitles and avatar."
        ),
    ),
    EvalCase(
        name="filler_heavy",
        input_text="ну это как бы вот так вот да нет ок",
        keywords=[],
        expect_subtitles=False,
        expect_avatar=False,
        expect_summary=False,
        baseline_subtitles=True,
        baseline_avatar=True,
        baseline_summary=True,
        category="noise",
        explanation=(
            "Filler-only sentence. No meaningful content. "
            "Agent rejects; baseline passes through."
        ),
    ),
    EvalCase(
        name="repeated_fragment",
        input_text="машинное обучение используется для классификации данных",
        keywords=["машинное", "обучение", "классификации"],
        expect_subtitles=False,
        expect_avatar=False,
        expect_summary=False,
        baseline_subtitles=True,
        baseline_avatar=True,
        baseline_summary=True,
        category="duplicate",
        explanation=(
            "Segment that repeats a recently accepted one. "
            "Agent suppresses duplicate; baseline shows it again."
        ),
    ),
    EvalCase(
        name="informative_short",
        input_text="Градиентный спуск минимизирует функцию потерь",
        keywords=["градиентный", "спуск", "потерь"],
        expect_subtitles=True,
        expect_avatar=True,
        expect_summary=False,  # short, score may not reach 0.40 threshold
        baseline_subtitles=True,
        baseline_avatar=True,
        baseline_summary=True,
        category="informative",
        explanation=(
            "Short but meaningful phrase. Agent shows in subtitles and avatar. "
            "Summary inclusion depends on importance score — borderline case."
        ),
    ),
    EvalCase(
        name="long_lecture_block",
        input_text=(
            "Свёрточные нейронные сети состоят из нескольких слоёв обработки. "
            "Каждый свёрточный слой извлекает локальные признаки входного изображения. "
            "Затем применяется операция пулинга для уменьшения размерности. "
            "Полносвязные слои выполняют финальную классификацию объектов."
        ),
        keywords=["свёрточные", "нейронные", "сети", "слоёв", "классификацию"],
        expect_subtitles=True,
        expect_avatar=True,
        expect_summary=True,
        baseline_subtitles=True,
        baseline_avatar=True,
        baseline_summary=True,
        category="informative",
        explanation=(
            "Long, content-rich lecture block. Agent routes to all outputs. "
            "Baseline also passes — but agent additionally scores it as high-importance "
            "and may trigger summary refresh."
        ),
    ),
    EvalCase(
        name="fragmented_bad_for_avatar",
        input_text="ну это да вот именно",
        keywords=[],
        expect_subtitles=False,
        expect_avatar=False,
        expect_summary=False,
        baseline_subtitles=True,
        baseline_avatar=True,
        baseline_summary=True,
        category="noise",
        explanation=(
            "Fragmented, meaningless input. Extremely bad for avatar — "
            "would produce garbled sign animation. Agent blocks entirely; "
            "baseline sends to avatar anyway."
        ),
    ),
    EvalCase(
        name="key_term_heavy",
        input_text=(
            "Трансформер использует механизм внимания attention для обработки "
            "последовательностей без рекуррентных слоёв"
        ),
        keywords=["трансформер", "внимания", "attention", "последовательностей"],
        expect_subtitles=True,
        expect_avatar=True,
        expect_summary=True,
        baseline_subtitles=True,
        baseline_avatar=True,
        baseline_summary=True,
        category="informative",
        explanation=(
            "High keyword density segment. Agent marks as important, "
            "highlights keywords, routes to all outputs."
        ),
    ),
    EvalCase(
        name="topic_ending_summary_refresh",
        input_text=(
            "Таким образом, мы рассмотрели основные архитектуры нейронных сетей: "
            "свёрточные, рекуррентные и трансформерные модели. "
            "Каждая из них имеет свои преимущества в зависимости от задачи. "
            "На следующей лекции мы перейдём к практическому обучению моделей."
        ),
        keywords=["архитектуры", "нейронных", "сетей", "свёрточные", "трансформерные"],
        expect_subtitles=True,
        expect_avatar=True,
        expect_summary=True,
        expect_refresh=False,  # refresh depends on accumulated budget, not single segment
        baseline_subtitles=True,
        baseline_avatar=True,
        baseline_summary=True,
        category="topic_end",
        explanation=(
            "Topic-ending block with summary-worthy content. "
            "Long enough to always be included in summary. "
            "Summary refresh may trigger depending on session word budget."
        ),
    ),
]
