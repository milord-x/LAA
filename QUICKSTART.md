# LAA Quick Start

Minimal local run flow for the Lecture Accessibility Agent.

## Install dependencies

```bash
pip install -r requirements.txt
```

## Configure environment

Copy the local environment file if the project expects one and set the ASR model, port, and any optional LLM variables you want to use.

## Start the app

```bash
python main.py
```

Default local address:

```text
http://127.0.0.1:8000
```

## Basic manual check

- open the app in a browser
- start a session
- allow microphone access
- speak a short phrase
- verify subtitle output appears
- verify agent stats endpoint responds

## Useful endpoints

- `GET /session/status`
- `GET /session/agent/stats`
- `GET /session/agent/recent-decisions`
- `GET /summary/current/live`
