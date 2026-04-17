# LAA – Lecture Accessibility Agent

An autonomous accessibility agent that transforms live speech into multiple accessible formats for people with hearing impairments.

Built as a competition prototype for **AI Agents Cup**.

<p align="center">
<img src="assets/IMG_6286.JPG" width="900">
</p>

---

## Problem

People with hearing impairments cannot effectively follow lectures, presentations, and public speech. Existing closed-caption tools produce raw text streams with noise, duplicates, and no structure – not an agent, just a transcription pipe.

---

## What LAA does

LAA listens to live audio and autonomously decides what to do with each segment:

- **Real-time subtitles** – filtered, deduplicated, shown immediately
- **Sign language avatar** – cleaned text routed to SiGML synthesis and rendered in the browser via CWASA
- **Session summary** – extractive summary built from accepted segments, refreshed automatically
- **Keyword highlights** – important terms annotated on subtitles

All routing decisions are made by the **Agent Layer** — not hardcoded rules, not manual configuration.

---

## Architecture

```
Browser (mic) — WebSocket — ws — subtitles
                    │
                    ▼
             core/pipeline.py
                    │
          ┌─────────┼─────────────┐
          │         │             │
        RMS        VAD           ASR
        gate      (Silero)    (Whisper)
          │         │             │
          └─────────┴─────────────┘
                    │
                    ▼
         processing/structurer.py
         (keyword extraction)
                    │
                    ▼
        ┌───────────────────────┐
        │    agent/             │
        │  AgentController      │  ← autonomous decision layer
        │    └─ AgentPolicy     │
        │       └─ AgentDecision│
        └───────────────────────┘
                    │
        ┌───────────┼────────────┐
        │           │            │
     subtitles    avatar      session
     (WebSocket) (SiGML/CWASA) transcript
                               │
                               ▼
                    processing/summarizer.py
                    (extractive summary)
```

---

## Agent Layer

The agent package (`agent/`) is the core differentiator.

Every ASR segment passes through `AgentController.process()` which invokes `AgentPolicy` – a rule-based scoring engine that produces an `AgentDecision` dataclass:

| Flag | Meaning |
|---|---|
| `include_in_subtitles` | Show to user |
| `include_in_avatar` | Send to sign-language synthesis |
| `include_in_summary` | Store in session transcript |
| `highlight_keywords` | Annotate with key terms |
| `refresh_summary` | Trigger live summary update |
| `is_noise` | Filler / hallucination / too short |
| `is_duplicate` | Repeats recent content |
| `importance_score` | 0–1 continuous relevance score |
| `reason` | Human-readable decision rationale |

### Why this is autonomous

- The agent runs on every segment without operator input
- Every decision has an explicit `reason` field – explainable, not a black box
- Routing to three independent output channels (subtitles / avatar / summary) is decided per-segment
- The agent suppresses duplicates across a sliding window of recent segments
- Summary refresh is triggered autonomously when accumulated word budget exceeds threshold
- All decisions are logged with structured traces for observability
- Runtime stats available at `GET /session/agent/stats`

### Policy rules

- Reject empty, too-short, or filler segments
- Reject noise patterns (single words, filler sounds: "uh", "um", "эм", "ага")
- Suppress duplicates via word-overlap ratio across recent window
- Compute importance score from: length bonus + keyword density + sentence completeness
- Route to avatar only when: ≥3 meaningful words, score ≥ 0.30, ≤40 words
- Include in summary when: score ≥ 0.40 or segment length ≥ 20 words
- Trigger summary refresh after 80 accepted words accumulated

---

## Optional LLM Refinement

LLM enhancement is available but **not required** – the agent works fully offline without it.

When `LAA_ENABLE_LLM=true` is set, `agent/llm_refiner.py` activates an optional post-routing stage:

- Rewrites raw ASR output into clean accessible text
- Condenses long speech blocks (>20 words) into 1-2 sentences
- Generates structured bullet-point notes from topic-ending segments

Any OpenAI-compatible API works (OpenAI, local llama.cpp, Ollama):

```env
LAA_ENABLE_LLM=true
LAA_LLM_PROVIDER=openai_compatible
LAA_LLM_MODEL=gpt-4o-mini
LAA_LLM_BASE_URL=https://api.openai.com/v1
LAA_LLM_API_KEY=sk-...
LAA_LLM_TIMEOUT=5.0
```

If LLM times out or fails, the original agent-routed text passes through unchanged.

**Hybrid architecture:**
```
rule-based policy core  →  optional LLM enhancement layer  →  outputs
```

---

## Evaluation

Benchmark results on 8 labeled test cases (`python evaluation/benchmark.py`):

| Metric | Baseline | Agent |
|--------|----------|-------|
| Segments to subtitles | 8/8 | 4/8 |
| Segments to avatar | 8/8 | 4/8 |
| Segments to summary | 8/8 | 4/8 |
| Noise/filler blocked | 0 | 3 |
| Duplicates suppressed | 0 | 1 |
| Expectation accuracy | — | 8/8 (100%) |

Full report: [`docs/evaluation_report.md`](docs/evaluation_report.md)

---

## Baseline vs Agent

Concrete side-by-side comparison of 8 cases showing what baseline (naive pass-through) does vs what the agent decides, and why the agent result is better for hearing-impaired users.

See [`docs/baseline_vs_agent.md`](docs/baseline_vs_agent.md)

---

## Stack

| Component | Technology |
|---|---|
| ASR | Whisper large-v3-turbo (OpenAI) |
| KZ/RU model | abilmansplus/whisper-turbo-kaz-rus-v1 |
| VAD | Silero VAD |
| Avatar | CWASA + SiGML (ISL sign dataset, 374+ signs) |
| Translation | argostranslate (offline RU/KZ → EN) |
| Backend | FastAPI + WebSockets |
| Summary | Extractive TF-based summarizer (offline) |
| Agent | Custom rule-based policy engine with explainable decisions |
| LLM (optional) | Any OpenAI-compatible API via httpx |

---

## API

| Endpoint | Description |
|---|---|
| `WS /ws/subtitles` | Audio input, subtitle + avatar output |
| `POST /session/start` | Start new session |
| `POST /session/stop` | Stop session |
| `POST /session/mode/{mode}` | Switch ASR language: auto / ru / en / kz |
| `GET /session/status` | Active session info |
| `GET /session/agent/stats` | Full agent statistics (accept/reject/avatar/summary/refresh counts) |
| `GET /session/agent/recent-decisions` | Last 20 agent decisions with routing flags and reasons |
| `GET /summary/{session_id}` | Full session summary |
| `GET /summary/current/live` | Live transcript |

---

## How to run

```bash
pip install -r requirements.txt

# copy and edit .env (set ASR_MODEL, PORT, etc.)
python main.py
# → http://localhost:8000
```

Open the browser, click **Start Session**, allow microphone, speak.

---

## AI Agents Cup – evaluation criteria

**Autonomy** – AgentController makes independent per-segment routing decisions across three output channels with no human-in-the-loop after session start.

**Technical depth** – multi-stage pipeline: RMS gate → Silero VAD → Whisper ASR → keyword extraction → agent policy scoring → conditional avatar synthesis + conditional session storage. Each stage has a clear, bounded responsibility.

**Explainability** – every agent decision carries a `reason` string and a `reasons` list of rule traces. The system can explain why any segment was accepted or rejected. Observable via `/session/agent/stats`.

**Practical value** – targets real accessibility needs for hearing-impaired users in lecture environments. Sign language output, live subtitles, and auto-summary work together as a unified accessible interface.
