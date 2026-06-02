# Jarvis Project Context

## Goal
Personal AI assistant inspired by Iron Man's Jarvis: voice interaction,
computer control, smart home integration.

## Stack
- Backend: FastAPI (Python 3.12)
- Frontend: TypeScript
- LLM: Claude API (Anthropic)
- STT: Whisper (local)
- TTS: ElevenLabs (later) / pyttsx3 (for now)
- Wake word: Porcupine (later)
- Storage: SQLite when needed, no Postgres
- No Docker for now

## Roadmap
1. HTTP /chat endpoint (text-in, text-out via Claude)
2. Add STT endpoint (Whisper)
3. Add TTS endpoint
4. Frontend mic capture + audio playback via HTTP
5. Refactor to WebSockets for streaming
6. Add tool use (open_app, search_web, etc.)
7. Wake word activation
8. UI polish

## Current stage
Stage 2 — STT (Whisper). Stage 1 (/chat endpoint) complete and committed;
adding multi-turn conversation history to /chat before starting STT.

## Conventions
- Virtual env in .venv/
- Secrets in .env (gitignored)
- requirements.txt pinned via pip freeze