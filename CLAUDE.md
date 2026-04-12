# CLAUDE.md

## Project identity
- Project name: **LAA**
- GitHub repository: `https://github.com/milord-x/LAA.git`
- Project type: **competition prototype / MVP**
- Priority: **win the contest**
- Status: active build under tight deadline

## Core mission
This project is being built for a competition. The objective is not to build a broad experimental system, but to deliver a **convincing, working, demo-ready product** that scores highly on usefulness, technical seriousness, autonomy, and presentation quality.

The project helps **people with hearing impairments** better understand speech in lectures and public environments.

The system must transform speech into accessible information with AI-assisted processing.

## Product goal
The product should help users who struggle to perceive spoken language by providing:
- real-time or near-real-time speech recognition
- accessible text subtitles
- sign-language visual output through an avatar pipeline
- automatic lecture/session summary
- useful structured outputs from speech, not just raw transcription

## Current chosen stack to test first
Keep these as the active first-line components unless there is a strong technical reason to replace them:
- **ASR baseline:** `Whisper large-v3-turbo`
- **KZ/RU booster:** `abilmansplus/whisper-turbo-kaz-rus-v1`
- **Avatar visual:** `SignLanguageSynthesis`

These are the current selected tools for first testing and validation.

## Scope discipline
This is a competition build. Do not expand scope carelessly.

Always optimize for:
1. working MVP
2. demo stability
3. practical usefulness
4. fast iteration
5. low token usage
6. low implementation risk

Do **not** drift into unnecessary research, overengineering, speculative rewrites, or optional platform complexity.

Do not wait for architecture from the user.
Do not ask the user to invent the structure for you.
You are responsible for creating a clean, minimal, competition-grade architecture based on the project goals and constraints.

## Token-efficiency rules
Work efficiently and minimize token usage.

Follow these rules:
- Keep reasoning compact and implementation-oriented.
- Avoid long explanations unless explicitly requested.
- Do not restate the project context repeatedly.
- Do not generate large exploratory plans when direct execution is possible.
- Prefer short status updates.
- Prefer concrete action over discussion.
- Read existing files before rewriting them.
- Rewrite only when necessary.
- Avoid producing duplicate code variants.
- Avoid unnecessary dependency churn.
- Avoid speculative abstractions.

When reporting progress, use concise technical summaries.

## Git discipline
Repository: `https://github.com/milord-x/LAA.git`

For **every code change**, make a **fast commit** with a **short commit message of 1-2 words**.

Requirements:
- commit after meaningful changes
- keep commit messages short
- avoid long commit messages
- examples: `init`, `subtitle ui`, `asr test`, `summary`, `avatar sync`

Do not leave large uncommitted code batches.

## Product understanding
You must understand the project as follows:
- It is an accessibility-focused AI system.
- It is intended for hearing-impaired users.
- It is aimed at lectures, presentations, and speech-heavy environments.
- It must combine practical value and technical credibility.
- It must be demo-friendly.
- It must be investor-presentable after the competition.
- It should be usable as a web product, with backend execution on the owner’s laptop/server.
- The site may be hosted separately, while inference/back-end logic can run locally.

## Delivery mindset
Build like this is a high-pressure competition submission.

Your priorities are:
- make it work
- make it stable
- make it understandable
- make it impressive in demo
- make it realistic under deadline

Do not optimize for theoretical perfection.
Optimize for a strong working result.

## Interaction rules
When working on this project:
- be decisive
- be practical
- be architecture-aware
- be conservative with scope
- surface risks clearly
- choose the path with the best deadline-to-impact ratio

If there are multiple options, prefer the one that:
- is faster to implement
- is easier to demo
- has lower failure risk
- preserves technical credibility

## What success means
Success is not “maximum research depth.”
Success is:
- a functioning MVP
- clear AI-agent value
- strong presentation quality
- competition readiness
- a realistic chance to place first

## Final operating rule
Act like the technical lead of a competition-critical prototype.
Take initiative, keep momentum, reduce waste, and move the project toward a winning demo.