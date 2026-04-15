# LAA Agent Evaluation Report

_Generated: 2026-04-15 04:43 UTC_

## Summary Metrics

| Metric | Baseline | Agent |
|--------|----------|-------|
| Segments sent to subtitles | 8/8 | 4/8 |
| Segments sent to avatar | 8/8 | 4/8 |
| Segments stored for summary | 8/8 | 4/8 |
| Duplicates suppressed | 0 | 1 |
| Noise/filler rejected | 0 | 3 |
| Summary refreshes triggered | 0 | 0 |
| Expectation matches | — | 8/8 |

**Agent accept rate:** 50%
**Noise segments blocked from avatar:** 4/8
**Expectation accuracy:** 8/8 (100%)

## Per-Case Results

| Case | Category | Baseline (sub/ava/sum) | Agent (sub/ava/sum) | Score | Verdict | Match |
|------|----------|------------------------|----------------------|-------|---------|-------|
| `noisy_fragment` | noise | Y/Y/Y | N/N/N | 0.00 | noise | ✓ |
| `filler_heavy` | noise | Y/Y/Y | N/N/N | 0.00 | noise | ✓ |
| `repeated_fragment` | duplicate | Y/Y/Y | N/N/N | 0.00 | duplicate | ✓ |
| `informative_short` | informative | Y/Y/Y | Y/Y/Y | 0.47 | accepted | ✓ |
| `long_lecture_block` | informative | Y/Y/Y | Y/Y/Y | 0.76 | accepted | ✓ |
| `fragmented_bad_for_avatar` | noise | Y/Y/Y | N/N/N | 0.00 | noise | ✓ |
| `key_term_heavy` | informative | Y/Y/Y | Y/Y/Y | 0.60 | accepted | ✓ |
| `topic_ending_summary_refresh` | topic_end | Y/Y/Y | Y/Y/Y | 0.79 | accepted | ✓ |

## Per-Case Detail

### `noisy_fragment`
- **Input:** _эм ааа ну_
- **Verdict:** noise (score=0.00)
- **Reason:** filler-heavy segment (>80% stopwords/fillers)
- **Routing:** subtitles=N avatar=N summary=N refresh=N
- **Why:** Pure noise/filler. Agent must reject entirely. Baseline would pass it to all outputs, polluting subtitles and avatar.

### `filler_heavy`
- **Input:** _ну это как бы вот так вот да нет ок_
- **Verdict:** noise (score=0.00)
- **Reason:** filler-heavy segment (>80% stopwords/fillers)
- **Routing:** subtitles=N avatar=N summary=N refresh=N
- **Why:** Filler-only sentence. No meaningful content. Agent rejects; baseline passes through.

### `repeated_fragment`
- **Input:** _машинное обучение используется для классификации данных_
- **Verdict:** duplicate (score=0.00)
- **Reason:** segment substantially repeats recent content
- **Routing:** subtitles=N avatar=N summary=N refresh=N
- **Why:** Segment that repeats a recently accepted one. Agent suppresses duplicate; baseline shows it again.

### `informative_short`
- **Input:** _Градиентный спуск минимизирует функцию потерь_
- **Verdict:** accepted (score=0.47)
- **Reason:** importance_score=0.47; SUBTITLES_YES; KEYWORDS_HIGHLIGHTED; AVATAR_YES; SUMMARY_
- **Routing:** subtitles=Y avatar=Y summary=Y refresh=N
- **Why:** Short but meaningful phrase. Agent shows in subtitles and avatar. Summary inclusion depends on importance score — borderline case.

### `long_lecture_block`
- **Input:** _Свёрточные нейронные сети состоят из нескольких слоёв обработки. Кажды_
- **Verdict:** accepted (score=0.76)
- **Reason:** importance_score=0.76; SUBTITLES_YES; KEYWORDS_HIGHLIGHTED; AVATAR_YES; SUMMARY_
- **Routing:** subtitles=Y avatar=Y summary=Y refresh=N
- **Why:** Long, content-rich lecture block. Agent routes to all outputs. Baseline also passes — but agent additionally scores it as high-importance and may trigger summary refresh.

### `fragmented_bad_for_avatar`
- **Input:** _ну это да вот именно_
- **Verdict:** noise (score=0.00)
- **Reason:** filler-heavy segment (>80% stopwords/fillers)
- **Routing:** subtitles=N avatar=N summary=N refresh=N
- **Why:** Fragmented, meaningless input. Extremely bad for avatar — would produce garbled sign animation. Agent blocks entirely; baseline sends to avatar anyway.

### `key_term_heavy`
- **Input:** _Трансформер использует механизм внимания attention для обработки после_
- **Verdict:** accepted (score=0.60)
- **Reason:** importance_score=0.60; SUBTITLES_YES; KEYWORDS_HIGHLIGHTED; AVATAR_YES; SUMMARY_
- **Routing:** subtitles=Y avatar=Y summary=Y refresh=N
- **Why:** High keyword density segment. Agent marks as important, highlights keywords, routes to all outputs.

### `topic_ending_summary_refresh`
- **Input:** _Таким образом, мы рассмотрели основные архитектуры нейронных сетей: св_
- **Verdict:** accepted (score=0.79)
- **Reason:** importance_score=0.79; SUBTITLES_YES; KEYWORDS_HIGHLIGHTED; AVATAR_YES; SUMMARY_
- **Routing:** subtitles=Y avatar=Y summary=Y refresh=N
- **Why:** Topic-ending block with summary-worthy content. Long enough to always be included in summary. Summary refresh may trigger depending on session word budget.

## Conclusion

The LAA agent rejected 38% of segments as noise/filler and suppressed 12% as duplicates. Avatar output was protected from 50% of unsuitable inputs. The baseline would have sent all 8 segments to every output channel, including noise, fillers, and repetitions — degrading subtitle quality and producing broken sign-language animations. The agent's routing accuracy vs expected behavior: 8/8 cases matched.