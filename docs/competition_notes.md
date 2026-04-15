# LAA — Конкурстық жұмыс бойынша ескертпелер

## AI Agents Cup бағалау критерийлеріне сәйкестік

---

### 1. Өзектілік (Актуальность)

- Есту қабілеті нашар адамдар үшін нақты проблема: дәрістерде, конференцияларда, жалпы орталарда сөзді қабылдауда қиындық
- Қазақстан мен ТМД елдерінде арнайы білім беру технологиялары нарығы әлі де жеткіліксіз
- Жүйе KZ/RU/EN тілдерін қолдайды — Қазақстан аудиториясы үшін маңызды
- Нақты пайдаланушыға: дәрісте отырып, субтитрлерді, белгі тілін және автоматты конспект алуы
- Тікелей орналастыруға дайын: браузерде жұмыс істейді, арнайы аппарат қажет емес

---

### 2. Студенттің үлесі (Вклад студента)

- Барлық негізгі модульдер нуллдан жазылған: `agent/`, `core/pipeline.py`, `asr/`, `avatar/`, `processing/`
- Агент policy және decision layer — авторлық дизайн, дайын фреймворкты пайдаланбады
- OpenAI-compatible LLM клиенті `httpx` арқылы жеке іске асырылды — SDK жоқ
- SiGML lookup базасы: 374+ белгілерді қолмен жинап, интеграциялады
- Evaluation benchmark жеке жазылды — дайын автоматты тестинг жоқ
- Frontend WebSocket + CWASA аватар интеграциясы — жеке іске асырылды

---

### 3. Техникалық тереңдік (Техническая проработка)

- **ASR pipeline:** Whisper large-v3-turbo + Silero VAD + RMS gate — үш деңгейлі аудио фильтрация
- **Agent layer:** AgentPolicy (rule-based scoring) → AgentController (orchestration) → AgentDecision (dataclass with full routing flags)
- **LLM refinement:** опционалды, OpenAI-compatible HTTP клиент, 5 сек таймаут, автоматты fallback
- **Sign synthesis:** RU/KZ → EN аудару (argostranslate, offline) → SiGML белгілер → CWASA аватар
- **Session management:** UUID сессиялары, transcript accumulation, lazy summary generation
- **Observability:** `/session/agent/stats` эндпоинті, recent\_reasons ring buffer, structured logging
- **26 unit тест:** agent policy, controller, counters, session reset, avatar routing — бәрі pass

---

### 4. Зерттеу тәсілі (Исследовательский подход)

- Benchmark: 8 тест-кейс, baseline vs agent comparison, JSON + markdown есеп
- Нәтижелер: agent 37.5% шуды блоктайды, 12.5% дубликаттарды басады, аватарды 50% сәйкессіз кірістен қорғайды
- Importance scoring компоненттері математикалық негізделген: `0.5 × length + 0.35 × keyword_density + 0.15 × sentence_completeness`
- Filler ratio threshold (≥80%) эмпирикалық тексерілді
- Baseline vs agent салыстыру: 8 нақты мысал, routing tablesiмен
- `docs/evaluation_report.md` — автоматты генерацияланатын бағалау есебі

---

### 5. Презентация сапасы (Качество презентации)

- README: проблема, архитектура диаграммасы, agent layer кестесі, API, қалай іске қосу
- `docs/baseline_vs_agent.md`: 8 нақты мысал, не неге жақсы екені — жюри оңай түсінеді
- `docs/evaluation_report.md`: сандық метрикалар, кесте, қорытынды — тікелей слайдқа қоюға болады
- `docs/architecture_for_jury.md`: техникалық схема мен pipeline жасырын жоқ
- `/session/agent/stats` эндпоинті: демо кезінде нақты сандар
- Барлық шешімдер explainable: `reason` жолы, `reasons` тізімі — "неге?" деген сұраққа жауап дайын

---

## Жюриге арналған негізгі тезистер

1. LAA — дауыс мәліметтерін бірнеше қол жетімді форматқа айналдыратын autonomous agent
2. Барлық routing шешімдер code арқылы тексеруге болады: `agent/policy.py`, `agent/decision.py`
3. LLM компоненті нақты жасалған, бірақ опционалды — желісіз режим сенімді жұмыс істейді
4. Benchmark нәтижелері: 8/8 кейс агент күтілген мінез-құлықты көрсетті
5. 26 unit тест бар, барлығы pass
6. Жүйе Қазақ/Орыс тілдерін нативті қолдайды
