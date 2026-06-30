# Jarvis Project Context

## Status — parked at Stage 5 #1 (2026-06-30)
Working checkpoint, not abandoned. **Built and shipped:** Stages 1–4 plus Stage 5
sub-project #1 (voice-driven, cancellable app-launching macros). Everything below
Stage 5 #1 in the roadmap — the management API/UI (#2/#3), Stage 8's multi-user
app, and the cross-cutting rigor tracks (auth, DB schema, observability, eval
harness) — is **planned, not built**. Read the roadmap as intent, not inventory.

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
8. User-facing app — a real, multi-user app people can actually use, not just
   the local `python -m app.voice` loop. Requirements:
   - One UI where a user can **type or talk** to Jarvis (text via the /chat
     path; speech via the ElevenLabs voice surface).
   - **Easy for anyone to try** — low-friction setup or a hosted demo.
   - **SQLite-backed, multi-user**: each user has their own list of recent
     conversation sessions, persisted across restarts. This is the trigger for
     the long-deferred Stage 1 SessionStore → SQLite swap, now widened to
     multi-user. "Like a real app."
   Open design questions (own brainstorm before building): user identity/auth;
   how in-browser voice relates to the current ElevenLabs local loop (embed the
   widget vs. the custom-LLM-proxy path in `docs/voice-architecture.md`); how it
   relates to the existing TS frontend and the Stage 5 #3 macro-management UI.
9. UI polish (of the Stage 8 app)

### Engineering-rigor bar (what makes this hireable, not just a demo)
Target reader: a **backend-focused software engineer who can also build AI**.
For that reader, *how* this is built matters more than how many features it has,
so the stages above are built to a **production bar, not demo-minimum**. Depth
over breadth — no commodity-tool padding (a dozen integrations doesn't impress;
one subsystem done rigorously does). These tracks cut **across** stages rather
than being features of their own:

- **Auth + multi-user data model** (lands in Stage 8): real authn/authz and
  per-user isolation, not a hardcoded user. The core backend showcase.
- **DB done properly**: a defensible schema (users / conversations / messages),
  indexing, migrations — not just "a SQLite store". Supersedes the Stage 1
  in-memory SessionStore.
- **API design rigor** (Stage 5 sub-project #2, Stage 8): Pydantic validation,
  correct status codes, consistent error envelopes, OpenAPI docs.
- **Observability**: structured logging + per-request token / cost / latency
  tracking, persisted to the same DB. A production concern with an AI twist.
- **Eval harness**: automated tests of *agent behavior* ("user says X → right
  tool / right answer"), not just unit tests. Rare in portfolios; high signal.
- **Security / guardrails**: Jarvis executes real commands on the machine —
  document the trust boundary, validate tool inputs, resist prompt injection.
  A standout story a plain chatbot project can't claim.
- **Concurrency story** (already built — needs articulating): async FastAPI +
  threaded tool execution + the cooperative cancel token (Stage 4 spike).

Deliberately **not** over-invested: the frontend stays minimal-but-working
(enough to be testable — it's "just there"); no breadth-for-breadth tools.

Companion project (own brainstorm, parked): a CV site with an AI chatbot over
**RAG** — the self-demonstrating front door, showing knowledge-retrieval depth
alongside Jarvis's action-taking depth.

## Current stage
**Parked at Stage 5 #1 (merged, PR #10).** Stage 5 — composite actions / macros,
sub-project #1 (storage + cancellable runner) shipped: `app/macro_store.py`
(SQLite behind a small interface), a `LaunchResult` refactor of `app/launcher.py`
+ a best-effort `is_running` (and path-style AppID launching for desktop apps like
JetBrains IDEs), `app/macros.py` (the cancellable run-loop with the idempotency
hybrid: skip if `is_running` OR launched within a 120s recency window, biased to
launch when unsure; supports per-app launch args like Chrome `--profile-directory`
via `{"app":..., "args":[...]}` entries), and a thin `run_macro` client tool. This
is the **first real consumer of the Stage 4 cancel token** — the run-loop polls
`token.cancelled` between app launches and keeps `token.set_progress()` a speakable
cumulative summary. 51 tests green; proven live via the Python path.

Sub-projects #2 (backend management API) and #3 (frontend macro UI) were
**deliberately not pursued** — the project is parked here. The only step left for a
full voice demo is the ElevenLabs dashboard wiring + mic acceptance for `run_macro`
(config, not code; see the macro plan's Task 5).

Stage 4 complete: the interruption spike (see `docs/voice-architecture.md`
"Spike results") confirmed the ElevenLabs SDK does not cancel an in-flight client
tool, so cancellation is LLM-driven — the agent calls a `cancel_action` client
tool that flips a shared cancel token (`app/cancellation.py`), which long-running
tools poll cooperatively between steps and report real partial progress. Verified
live: "stop" mid-action halts the tool early and the agent truthfully reports how
far it got.

Stage 3 complete (PR #8): `open_app` executes on-device and its result
round-trips back to the agent. Stage 2 complete (PR #6): ElevenLabs Agent runs
with Claude as its LLM, voice loop works end-to-end via `app/voice.py`. Stage 1
(/chat) complete, with multi-turn history via an in-memory SessionStore (PR #1).

Stage 5 design note (built as `run_macro` / `app/macros.py`): the runner is a
loop with poll points between steps (checks the cancel token between each app
launch), records per-step progress, and skips already-satisfied apps via the
idempotency hybrid so an interrupted-then-rerun macro doesn't double-launch. When
a second concurrent cancellable action appears, the single-slot cancel token (one
`_current`) becomes a `tool_call_id`-keyed registry — `app/cancellation.py`'s
`begin()` prints a warning the moment that limit is exceeded.

Known deferrals from Stage 1 (revisit when they bite):
- SessionStore is in-memory only — history is lost on restart, not shared
  across workers. Swap to SQLite behind the same interface when persistence
  is needed. (Note: ElevenLabs now manages conversation history; this matters
  only for the text /chat fallback or a custom-LLM proxy.) **This is now
  scheduled work, not just a deferral — it's the storage layer for the Stage 8
  user-facing app (per-user persisted session lists).**
- No conversation-history trimming; token cost grows per turn.

## Conventions
- Virtual env in .venv/
- Secrets in .env (gitignored)
- requirements.txt pinned via pip freeze
- CI (.github/workflows/ci.yml) runs pytest on PRs to main; main is
  protected and requires the `test` check to pass before merge
- Merge style: squash (one commit per PR on main)