# Jarvis Project Context

## Status — active; single-user local assistant (2026-07-01)
**Direction change (was: "parked at Stage 5 #1").** Jarvis is being built out as a
**single-user, local desktop personal assistant** — a real tool to actually use,
not a multi-user portfolio app. **Built and shipped to `main`:** Stages 1–5 #1,
an action-capable **web UI with memory** (PR #12), **Porcupine wake word**
(PR #13), the backend **management API** (PR #14, Stage 5 #2), and **Stage 6
tools** — `search_web` + `control_system` (PR #16). **Dropped by explicit
decision:** Stage 8's multi-user app, auth/authz, and security hardening (see the
rigor-bar note below). **Next track is the frontend management UI (Stage 5 #3)** —
the last real feature track; everything else left is verification or optional
(see Current stage). Read the roadmap as history + intent, not inventory.

## Goal
Personal AI assistant inspired by Iron Man's Jarvis: voice interaction,
computer control, smart home integration. Scoped to **single-user, local** —
runs on Robert's machine, no accounts.

## Stack
- Backend: FastAPI (Python 3.12)
- Frontend: vanilla HTML/CSS/JS in `app/static/` (type-or-talk page, Web Speech
  API for browser speech). Kept minimal-but-working on purpose.
- LLM: Claude (Anthropic). Two paths: the **ElevenLabs Agent's LLM** for the
  voice loop, and a **server-side Claude tool-use loop** (`app/agent.py`) behind
  the `/chat` web path.
- Voice loop (STT + TTS + turn-taking + barge-in + AEC): ElevenLabs Agents
- Local actions: client tools executed on-device (`open_app`, `run_macro`,
  `cancel_action`, `remember`) — shared between the voice and text paths
- Wake word: **Porcupine "jarvis"** (`app/wake.py`) — built (PR #13); gates the
  ElevenLabs session so nothing runs/costs while idle
- Storage: **SQLite in use** — `jarvis.db` (conversations, messages, memories),
  `macros.db` (macros); both gitignored. No Postgres.
- No Docker for now

Voice architecture decision and rationale: see `docs/voice-architecture.md`.

## Roadmap
Revised 2026-06-15 after the ElevenLabs-owns-the-voice-loop pivot (see
`docs/voice-architecture.md`); status updated 2026-07-01. The old "build the
pipeline ourselves" plan (Whisper STT, local TTS, WebSocket streaming) is
superseded.

1. HTTP /chat endpoint (text-in, text-out via Claude) — **done** (PR #1). Now a
   full server-side tool-use loop (`app/agent.py`), the web UI's backend.
2. ElevenLabs Agent with Claude as the LLM (voice loop end-to-end) — **done**
   (PR #6); `app/voice.py` runs the loop, verified mic → STT → Claude → TTS.
3. Local client-tool executor; first tool `open_app` — **done** (PR #8).
4. Interruption-vs-in-flight-action spike + cancellation — **done** (PR #9);
   SDK won't cancel in-flight tools, so cancellation is LLM-driven via a
   `cancel_action` tool + cooperative cancel token.
5. Composite actions / macros — **#1 storage + cancellable runner done** (PR #10,
   `run_macro`); **#2 backend management API done** (PR #14); **#3 frontend
   macro-management UI is the next track.**
6. More tools — **`search_web` (Tavily) + `control_system` (volume/media/lock/
   sleep) done** (PR #16). Smart home / other integrations not built (optional
   breadth).
7. Wake word activation — **done** (PR #13, Porcupine); pending live mic
   acceptance on Robert's machine (see Current stage).
8. ~~User-facing multi-user app~~ — **DROPPED.** Superseded by the single-user
   local direction. The useful parts (type-or-talk UI, SQLite persistence)
   landed single-user in PR #12; the multi-user / hosted-demo / per-user-auth
   ambition is not being pursued.
9. UI polish — deferred (of the single-user web UI).

### Engineering-rigor bar — revised after the single-user pivot
Original framing targeted a **backend engineer who can also build AI**, with
**auth + multi-user** as the core showcase. That framing is **downgraded**: the
project is now a single-user local tool, so **auth/authz, per-user isolation,
and security hardening are deliberately not built** (Robert's explicit call —
the machine-trust boundary is "it's my machine"). What still carries the
"built well, not demo-minimum" signal:

- **API design rigor** (Stage 5 #2 / PR #14): Pydantic validation at the
  boundary (incl. a `str | {app,args}` macro union), correct status codes
  (201/409/200/204/404/422), consistent `{"detail": ...}` error envelope,
  OpenAPI docs. **Built.**
- **DB done reasonably**: indexed SQLite schema (conversations / messages /
  memories / macros) behind thin store modules. Single-user, so no users table
  or migrations story. **Built.**
- **Concurrency story** (built — needs articulating): async FastAPI + threaded
  tool execution + the cooperative cancel token (Stage 4).
- **Observability** (structured logging + per-request token/cost/latency to the
  DB): **considered, deferred** — not built, and no longer load-bearing.
- **Eval harness** (tests of agent behavior): **not built**; still a nice-to-have.
- **Guardrails / tool-input validation**: partial via the API-boundary
  validation; prompt-injection hardening not pursued (single-user trust model).

Frontend stays minimal-but-working (testable, "just there").

Companion project (own brainstorm, parked): a CV site with an AI chatbot over
**RAG** — the self-demonstrating front door.

## Current stage
**Backend feature-complete.** The only real feature track left is the **frontend
management UI (Stage 5 #3)** — a page to edit macros, prune memories, and delete
conversations against the management API. Everything else outstanding is either
**verification** (wake-word mic + `control_system` WSL→Windows interop, both
manual on Robert's machine), **optional** (Sub-project B packaging as a
tray/autostart app; smart-home tools), or **deliberately deferred** (observability,
eval harness — see rigor-bar note).

**PR #16 (merged) — Stage 6 tools.** `search_web` (Tavily, `app/web_search.py`)
and `control_system` (`app/system_control.py`: volume/media/lock/sleep run from
WSL via `powershell.exe` SendKeys + `rundll32.exe`), both wired into voice
(`build_client_tools()`) and text (`agent.py`). Each returns a string and never
raises into the agent loop; injectable seams keep tests off the network/OS.
**Live-unverified:** `control_system` depends on WSL→Windows interop (fails
gracefully if off). Needs `TAVILY_API_KEY` + EL dashboard tool declarations.

**PR #14 (merged) — backend management API (Stage 5 #2).** Macro CRUD in a
dedicated router (`app/macros_api.py`, `POST`=create/409, `PUT`=upsert, `DELETE`);
memory `GET /jarvis/memories` returns `[{id, content, created_at}]` plus
`DELETE /jarvis/memories/{id}`; `DELETE /jarvis/conversations/{session_id}` (row +
messages). New store fns: `macro_store.create_macro`/`delete_macro`,
`memory_store.list_memories_detailed`/`delete_memory`,
`conversation_store.delete_conversation`. `list_memories() -> list[str]`
deliberately unchanged (the agent/voice prompt-injection path depends on it).
Built subagent-driven TDD, whole-branch review clean.

**PR #13 (merged) — wake word + voice memory.** Porcupine "jarvis" (`app/wake.py`)
gates a reusable memory-aware `run_session()` in `app/voice.py` that bridges saved
memories into the ElevenLabs session via `send_contextual_update`; shared
`remember` tool across voice + text. **Open item (manual, Robert's machine):**
live mic acceptance — Picovoice key in `.env`, declare a `remember` client tool on
the EL agent, `python -m app.wake`. **Risk: pvrecorder getting the mic through
WSL2 audio is unverified.**

**PR #12 (merged) — action-capable web UI with memory.** `/chat` runs the
`app/agent.py` Claude tool-use loop executing `open_app`/`run_macro`/
`cancel_action`/`remember` server-side; SQLite `conversation_store` +
`memory_store`; a vanilla type-or-talk web page (`app/static/`). **This shipped
the long-deferred SessionStore → SQLite swap** (single-user, not multi-user).

**PR #10 (merged) — Stage 5 #1 macros.** `app/macro_store.py` (SQLite behind a
small interface), a `LaunchResult` refactor of `app/launcher.py` + best-effort
`is_running` (and path-style AppID launching for desktop apps like JetBrains
IDEs), `app/macros.py` (the cancellable run-loop with the idempotency hybrid:
skip if `is_running` OR launched within a 120s recency window, biased to launch
when unsure; per-app args like Chrome `--profile-directory` via `{"app":...,
"args":[...]}` entries), and a thin `run_macro` client tool. **First real
consumer of the Stage 4 cancel token** — polls `token.cancelled` between launches
and keeps `token.set_progress()` a speakable cumulative summary.

**Stage 4 (merged, PR #9) — cancellation.** The interruption spike (see
`docs/voice-architecture.md` "Spike results") confirmed the EL SDK does not
cancel an in-flight client tool, so cancellation is LLM-driven — the agent calls
`cancel_action`, which flips a shared token (`app/cancellation.py`) that
long-running tools poll cooperatively and report real partial progress. When a
second concurrent cancellable action appears, the single-slot token (one
`_current`) becomes a `tool_call_id`-keyed registry; `begin()` warns when that
limit is exceeded. Verified live.

**Stages 1–3 (merged):** Stage 3 (PR #8) `open_app` executes on-device, result
round-trips back. Stage 2 (PR #6) EL Agent + Claude voice loop end-to-end. Stage
1 (PR #1) `/chat` with multi-turn history (originally in-memory; now SQLite).

**Deferrals still open:**
- No conversation-history trimming; token cost grows per turn.
- Observability / eval harness not built (see rigor-bar note).

## Conventions
- Virtual env in .venv/
- Secrets in .env (gitignored)
- requirements.txt pinned via pip freeze
- CI (.github/workflows/ci.yml) runs pytest on PRs to main; main is
  protected and requires the `test` check to pass before merge
- Merge style: squash (one commit per PR on main)
