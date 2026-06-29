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
3. Local client-tool executor (Python SDK); first tool: open_app — done
   (PR #8); result round-trips back to the agent, failure path verified
4. Interruption-vs-in-flight-action spike + cancellation handling — done;
   spike confirmed the SDK won't cancel in-flight tools, so cancellation is
   LLM-driven via a `cancel_action` tool + cooperative cancel token
5. Composite actions / macros (open_work_environment) — first real consumer
   of the cancel token
6. More tools (search_web, smart home, etc.)
7. Wake word activation (evaluate ElevenLabs vs Porcupine)
8. UI polish

## Current stage
Stage 5 — composite actions / macros. Stage 4 complete: the interruption spike
(see `docs/voice-architecture.md` "Spike results") confirmed the ElevenLabs SDK
does not cancel an in-flight client tool, so cancellation is LLM-driven — the
agent calls a `cancel_action` client tool that flips a shared cancel token
(`app/cancellation.py`), which long-running tools poll cooperatively between
steps and report real partial progress. Verified live: "stop" mid-action halts
the tool early and the agent truthfully reports how far it got. The cancel
machinery is wired into `voice.py` via `build_client_tools()` but dormant until
Stage 5 adds a long-running action to cancel (`open_app` is too fast to need it).

Stage 3 complete (PR #8): `open_app` executes on-device and its result
round-trips back to the agent. Stage 2 complete (PR #6): ElevenLabs Agent runs
with Claude as its LLM, voice loop works end-to-end via `app/voice.py`. Stage 1
(/chat) complete, with multi-turn history via an in-memory SessionStore (PR #1).

Stage 5 design note: `open_work_environment` is the first real cancellable
macro. Build it as a loop with poll points between steps (check the cancel token
between each app launch), record per-step progress, and make steps idempotent so
an interrupted-then-rerun macro doesn't double-launch. When a second concurrent
cancellable action appears, the single-slot cancel token (one `_current`) becomes
a `tool_call_id`-keyed registry — `app/cancellation.py`'s `begin()` prints a
warning the moment that limit is exceeded.

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