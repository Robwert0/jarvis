# Jarvis Project Context

## Goal
Personal AI assistant inspired by Iron Man's Jarvis: voice interaction,
computer control, smart home integration.

## Stack
- Backend: FastAPI (Python 3.12)
- Frontend: TypeScript
- LLM: Claude (Anthropic) — runs as the ElevenLabs Agent's LLM (native option
  to start; custom-LLM proxy as an escape hatch)
- Voice loop (STT + TTS + turn-taking + barge-in + AEC): ElevenLabs Agents
- Local actions: ElevenLabs client tools, executed on-device via the Python SDK
- Wake word: Porcupine (later) — re-evaluate, ElevenLabs may cover activation
- Storage: SQLite when needed, no Postgres
- No Docker for now

Voice architecture decision and rationale: see `docs/voice-architecture.md`.

## Roadmap
Revised 2026-06-15 after the ElevenLabs-owns-the-voice-loop pivot (see
`docs/voice-architecture.md`). The old "build the pipeline ourselves" plan
(Whisper STT, local TTS, WebSocket streaming) is superseded.

1. HTTP /chat endpoint (text-in, text-out via Claude) — done, kept as text
   fallback / future custom-LLM proxy
2. Stand up an ElevenLabs Agent with Claude as the LLM (voice loop working
   end-to-end with a basic prompt, no actions yet) — done (PR #6); `app/voice.py`
   runs the loop, verified mic -> STT -> Claude -> TTS -> speaker
3. Local client-tool executor (Python SDK); first tool: open_app
4. Composite actions / macros (open_work_environment)
5. Interruption-vs-in-flight-action spike + cancellation handling
6. More tools (search_web, smart home, etc.)
7. Wake word activation (evaluate ElevenLabs vs Porcupine)
8. UI polish

## Current stage
Stage 3 — local client-tool executor. Stage 2 complete (PR #6): the ElevenLabs
Agent runs with Claude as its LLM and the voice loop works end-to-end via
`app/voice.py` (mic -> STT -> Claude -> TTS -> speaker). Stage 1 (/chat) complete,
including multi-turn conversation history via an in-memory SessionStore (PR #1).

First concrete step before building the executor: run the interruption spike
from `docs/voice-architecture.md` (barge in during a slow client tool, observe
what fires) — it de-risks the whole action-cancellation design.

Known deferrals from Stage 1 (revisit when they bite):
- SessionStore is in-memory only — history is lost on restart, not shared
  across workers. Swap to SQLite behind the same interface when persistence
  is needed. (Note: ElevenLabs now manages conversation history; this matters
  only for the text /chat fallback or a custom-LLM proxy.)
- No conversation-history trimming; token cost grows per turn.

## Conventions
- Virtual env in .venv/
- Secrets in .env (gitignored)
- requirements.txt pinned via pip freeze
- CI (.github/workflows/ci.yml) runs pytest on PRs to main; main is
  protected and requires the `test` check to pass before merge
- Merge style: squash (one commit per PR on main)