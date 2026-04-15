# LAA — Жюриге арналған архитектура сипаттамасы

## Жүйенің мақсаты

LAA — есту қабілеті нашар пайдаланушыларға арналған autonomous accessibility agent. Тікелей дауыс ағынын қабылдап, бірнеше қолжетімді форматта шығаруды автоматты түрде басқарады.

---

## Pipeline қадамдары

```
Браузер (микрофон)
        │
        │ WebSocket /ws/subtitles (binary LAA protocol)
        ▼
┌─────────────────────────────────────────────────┐
│              core/pipeline.py                   │
│                                                 │
│  1. Frame parsing (LAA header / raw PCM)        │
│  2. Resampling → 16 kHz                         │
│  3. RMS gate (silence detection)                │
│  4. Silero VAD (voice activity detection)       │
│  5. Whisper ASR (large-v3-turbo)                │
│  6. Hallucination filter (exact + substring)    │
│                                                 │
└─────────────────────┬───────────────────────────┘
                      │ ASR text
                      ▼
┌─────────────────────────────────────────────────┐
│         processing/structurer.py                │
│  Keyword extraction (frequency-based, TF)       │
└─────────────────────┬───────────────────────────┘
                      │ text + keywords
                      ▼
┌═════════════════════════════════════════════════╗
║           AGENT LAYER (agent/)                  ║
║                                                 ║
║  AgentController.process(text, keywords)        ║
║    │                                            ║
║    ▼                                            ║
║  AgentPolicy.evaluate_segment()                 ║
║    ├─ Stage 1: Hard-reject gates                ║
║    │    empty? → EMPTY_SEGMENT                  ║
║    │    filler word? → FILLER_WORD              ║
║    │    filler-heavy? → FILLER_HEAVY            ║
║    │    too few words? → TOO_SHORT              ║
║    │                                            ║
║    ├─ Stage 2: Duplicate suppression            ║
║    │    word-overlap ≥ 0.75? → DUPLICATE        ║
║    │                                            ║
║    ├─ Stage 3: Importance scoring               ║
║    │    score = 0.5×length + 0.35×kw + 0.15×sent║
║    │                                            ║
║    └─ Stage 4: Routing decisions                ║
║         include_in_subtitles                    ║
║         include_in_avatar (≥3 words, ≥0.30)    ║
║         include_in_summary (≥0.40 or ≥20 words)║
║         highlight_keywords                      ║
║         refresh_summary (budget ≥ 80 words)    ║
║                                                 ║
║  Returns: AgentDecision (dataclass)             ║
║    .importance_score: float                     ║
║    .reason: str                                 ║
║    .reasons: list[str]   ← explainability       ║
╚═════════════════════════════════════════════════╝
                      │ AgentDecision
                      ▼
         ┌────────────┼──────────────┐
         │            │              │
         ▼            ▼              ▼
  [subtitles]    [avatar/sign]  [session/summary]
  WebSocket      RU/KZ→EN         transcript
  JSON payload   translate        append
                 SiGML lookup
                 CWASA render
                      │
                      ▼ (optional, if LAA_ENABLE_LLM=true)
              agent/llm_refiner.py
              OpenAI-compatible API
              refine / condense / notes
              (fallback → extractive)
```

---

## Policy Engine жұмысы

Policy engine — бұл жай фильтр емес, бағалау жүйесі:

| Ереже | Шарт | Нәтиже |
|-------|------|--------|
| Empty gate | len < 8 char | EMPTY_SEGMENT |
| Filler exact | word ∈ {да, ну, ок, um, uh...} | FILLER_WORD |
| Filler heavy | ≥80% stopwords/fillers | FILLER_HEAVY |
| Too short | meaningful words < 2 | TOO_SHORT |
| Duplicate | overlap ratio ≥ 0.75 | DUPLICATE_SUPPRESSED |
| Avatar gate | words < 3 OR score < 0.30 | AVATAR_SKIPPED |
| Summary gate | score < 0.40 AND words < 20 | SUMMARY_SKIPPED |
| Keyword flag | density ≥ 0.25 OR score ≥ 0.50 | KEYWORDS_HIGHLIGHTED |
| Refresh gate | budget ≥ 80 words | SUMMARY_REFRESH |

---

## LLM компонентінің рөлі

`agent/llm_refiner.py` — агент жүйесін күшейтетін опционалды қабат:

- `LAA_ENABLE_LLM=true` болса ғана белсенді
- Whisper шығысын қолжетімді мәтінге қайта жазу
- Ұзын блоктарды 1-2 сөйлемге қысу
- Тақырып аяқталғанда bullet-point конспект жасау
- Fallback: LLM қол жетімсіз болса → extractive summarizer

Бұл жүйені "LLM-enhanced autonomous agent" деп сипаттауға мүмкіндік береді, бірақ LLM жоқ болса да жұмыс істейді.

---

## Жүйе неге autonomous?

1. **Шешімдер адам қатысусыз қабылданады** — сессия басталғаннан кейін оператор ешнәрсе баптамайды
2. **Әрбір шешімнің негіздемесі бар** — `reason` жолы, `reasons` тізімі, structured logging
3. **Үш тәуелсіз арналарды басқарады** — subtitles, avatar, summary — әр сегмент үшін жеке
4. **Жинақталған контекстке негізделеді** — word budget, recent window, session state
5. **Runtime статистика** — `/session/agent/stats` accept/reject сандарын нақты уақытта береді

---

## Бұл жай wrapper емес

API-ды тікелей шақыратын жүйеден айырмашылығы:

| Wrapper | LAA |
|---------|-----|
| ASR → субтитр | ASR → agent policy → conditional routing |
| Барлығын береді | Шуды, дубликаттарды, маңызсызды блоктайды |
| Шешімдер жоқ | AgentDecision — explicit flags + reason |
| LLM = жүйенің өзегі | LLM = опционалды қабат, агент онсыз жұмыс істейді |
| Метрика жоқ | Benchmark, importance score, accept rate |

---

## Evaluation нәтижелері (8 test case)

| Метрика | Baseline | Agent |
|---------|----------|-------|
| Subtitles жіберілді | 8/8 | 4/8 |
| Avatar жіберілді | 8/8 | 4/8 |
| Summary жазылды | 8/8 | 4/8 |
| Шу блокталды | 0 | 3 |
| Дубликат басылды | 0 | 1 |
| Күтілген мінез-құлық | — | 8/8 (100%) |
