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
Stage 2 — STT (Whisper). Stage 1 (/chat) complete, including multi-turn
conversation history via an in-memory SessionStore (merged in PR #1).
Next: add a Whisper transcription endpoint and wire audio -> text -> /chat.

Known deferrals from Stage 1 (revisit when they bite):
- SessionStore is in-memory only — history is lost on restart, not shared
  across workers. Swap to SQLite behind the same interface when persistence
  is needed.
- No conversation-history trimming; token cost grows per turn.

## Conventions
- Virtual env in .venv/
- Secrets in .env (gitignored)
- requirements.txt pinned via pip freeze
- CI (.github/workflows/ci.yml) runs pytest on PRs to main; main is
  protected and requires the `test` check to pass before merge
- Merge style: squash (one commit per PR on main)