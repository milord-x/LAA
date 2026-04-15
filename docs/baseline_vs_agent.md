# Baseline vs Agent Mode — LAA Comparison

## What is Baseline?

A naive speech-to-output pipeline with no agent layer:

- Every ASR segment goes to **subtitles** unconditionally
- Every ASR segment goes to **avatar/sign synthesis** unconditionally
- Every ASR segment is stored for **summary** unconditionally
- No noise filtering, no duplicate suppression, no importance scoring
- Equivalent to a simple "pass-through" transcription service

## What is Agent Mode?

The LAA autonomous agent applies per-segment routing decisions:

- `AgentPolicy` evaluates each segment with a multi-rule scoring engine
- `AgentController` routes to subtitles / avatar / summary independently
- Noise, fillers, and duplicates are rejected before reaching any output
- Importance score (0–1) determines routing for borderline segments
- All decisions are logged with explicit `reason` traces
- Summary refresh is triggered autonomously after semantic budget accumulates

---

## Concrete Examples

### 1. Pure noise fragment

| | Input | Subtitles | Avatar | Summary |
|--|-------|-----------|--------|---------|
| **Baseline** | "эм ааа ну" | ✓ shows | ✓ sends | ✓ stores |
| **Agent** | "эм ааа ну" | ✗ blocked | ✗ blocked | ✗ blocked |

**Why agent is better:** Baseline generates empty/garbled sign animation and pollutes the subtitle stream. Agent detects 100% filler ratio and rejects entirely. `reason: filler-heavy segment (>80% stopwords/fillers)`

---

### 2. Filler-heavy utterance

| | Input | Subtitles | Avatar | Summary |
|--|-------|-----------|--------|---------|
| **Baseline** | "ну это как бы вот так вот да нет ок" | ✓ shows | ✓ sends | ✓ stores |
| **Agent** | same | ✗ blocked | ✗ blocked | ✗ blocked |

**Why agent is better:** This is a common speech disfluency. Zero semantic content. Baseline would show meaningless text to a hearing-impaired user. Agent classifies as `FILLER_HEAVY` and suppresses.

---

### 3. Duplicate segment

| | Input | Subtitles | Avatar | Summary |
|--|-------|-----------|--------|---------|
| **Baseline** | "машинное обучение используется для классификации данных" (2nd time) | ✓ shows again | ✓ sends again | ✓ stores again |
| **Agent** | same | ✗ suppressed | ✗ suppressed | ✗ suppressed |

**Why agent is better:** Whisper sometimes repeats recent output. Baseline duplicates the subtitle and stores redundant text in summary. Agent detects word-overlap ratio ≥ 0.75 and suppresses. `reason: DUPLICATE_SUPPRESSED`

---

### 4. Short but informative phrase

| | Input | Subtitles | Avatar | Summary |
|--|-------|-----------|--------|---------|
| **Baseline** | "Градиентный спуск минимизирует функцию потерь" | ✓ | ✓ | ✓ |
| **Agent** | same | ✓ | ✓ | ✓ (score=0.47) |

**Why agent is better:** Both show it — but agent additionally scores it as 0.47 importance, highlights keywords (`градиентный`, `спуск`, `потерь`), and attaches structured metadata to the payload. Baseline shows raw text without context.

---

### 5. Long lecture block

| | Input | Subtitles | Avatar | Summary |
|--|-------|-----------|--------|---------|
| **Baseline** | 4-sentence CNN architecture explanation | ✓ | ✓ | ✓ |
| **Agent** | same | ✓ | ✓ | ✓ (score=0.76, KEYWORDS_HIGHLIGHTED) |

**Why agent is better:** Both route to all outputs — but agent marks as `importance=0.76`, highlights 5 key terms, and includes `refresh_summary` flag when session budget is reached. Downstream can use this for live summary updates.

---

### 6. Fragmented input dangerous for avatar

| | Input | Subtitles | Avatar | Summary |
|--|-------|-----------|--------|---------|
| **Baseline** | "ну это да вот именно" | ✓ shows | ✓ sends | ✓ stores |
| **Agent** | same | ✗ blocked | ✗ blocked | ✗ blocked |

**Why agent is better:** This type of input produces **broken sign-language animation** in CWASA — individual filler words map to no SiGML signs or produce random gestures. Agent detects `FILLER_HEAVY` and protects the avatar output entirely.

---

### 7. Key-term-dense input

| | Input | Subtitles | Avatar | Summary |
|--|-------|-----------|--------|---------|
| **Baseline** | "Трансформер использует механизм внимания attention для обработки последовательностей без рекуррентных слоёв" | ✓ | ✓ | ✓ |
| **Agent** | same | ✓ | ✓ | ✓ (score=0.60, KEYWORDS_HIGHLIGHTED) |

**Why agent is better:** Agent recognizes high keyword density (трансформер, внимания, attention, последовательностей), marks segment as important, highlights keywords in payload. Frontend can render these differently (bold, color) for better accessibility.

---

### 8. Topic-ending summary block

| | Input | Subtitles | Avatar | Summary |
|--|-------|-----------|--------|---------|
| **Baseline** | 4-sentence topic wrap-up | ✓ | ✓ | ✓ (flat append) |
| **Agent** | same | ✓ | ✓ | ✓ (score=0.79) + `refresh_summary=True` when budget full |

**Why agent is better:** Agent recognizes high-importance block and triggers `refresh_summary` flag after accumulated word budget exceeds threshold (80 words). This allows the frontend or summary endpoint to generate an updated live summary at the right moment — not just at session end.

---

## Summary Table

| Case | Baseline avatar outputs | Agent avatar outputs | Agent advantage |
|------|------------------------|----------------------|-----------------|
| Pure noise | sends | blocks | prevents broken animation |
| Filler utterance | sends | blocks | protects subtitle quality |
| Duplicate | sends again | suppresses | prevents redundancy |
| Short informative | sends | sends + metadata | adds importance score, keywords |
| Long lecture | sends | sends + high score | triggers summary refresh signal |
| Fragmented filler | sends | blocks | prevents garbled signs |
| Key-term dense | sends | sends + highlighted | enables richer UI rendering |
| Topic wrap-up | flat append | sends + refresh flag | enables timely live summary |

---

## Conclusion

The baseline model treats every ASR output as equally valid and sends it everywhere.
The agent model treats each segment as a routing decision with an explicit rationale.

Key measured differences on the 8-case benchmark:

- **Noise/filler rejection:** 0% (baseline) → 37.5% (agent)
- **Duplicate suppression:** 0% → 12.5%
- **Avatar protection rate:** 0% → 50% (half of inputs blocked from sign synthesis)
- **Importance annotation:** none → 0.0–0.79 score per segment
- **Explainability:** none → every decision has a `reason` string and rule trace

The agent does not just filter more aggressively — it makes the system *accessible* in a meaningful sense: hearing-impaired users see clean, deduplicated subtitles; sign language output is produced only from suitable clean text; summaries reflect the actual content of the session, not transcription noise.
