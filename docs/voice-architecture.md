# Voice Architecture Decision: ElevenLabs Agent + Claude-as-Brain

Status: **Decided** (2026-06-15). Supersedes the original "build the voice
pipeline ourselves" roadmap (Whisper STT → Claude → TTS over WebSockets).

## TL;DR

Hand the **entire voice/conversation loop** to ElevenLabs Agents (formerly
Conversational AI). Keep **Claude as the single brain** — it both converses and
decides on actions. Actions (open apps, web search, "open work environment"
macros) run **locally on the user's machine** via ElevenLabs **client tools**.

```
  ┌─────────────────────────── ElevenLabs Agent (cloud) ───────────────────────────┐
  │   mic ─► STT ─► [ Claude LLM ] ─► TTS ─► speaker                                 │
  │                      │  turn-taking, barge-in, AEC all handled here              │
  └──────────────────────┼──────────────────────────────────────────────────────────┘
                         │ client tool call  (e.g. open_app("spotify"))
                         ▼
  ┌──────────────────────────── Local executor (user's machine) ───────────────────┐
  │   ElevenLabs Python SDK  ──►  registered tools: open_app, open_work_environment,│
  │                               search_web, ...  (execute locally, return result) │
  └─────────────────────────────────────────────────────────────────────────────────┘
```

## Why this over rolling our own pipeline

We seriously considered building the loop ourselves (Whisper → streaming Claude
→ streaming TTS, with our own barge-in). The blocker was **acoustic echo
cancellation (AEC)**: to support barge-in over open speakers (not just
headphones), the mic stays open while Jarvis talks and would hear itself. Good
AEC is genuinely hard and is exactly the part ElevenLabs has already solved.

Letting ElevenLabs own the *audio* loop sidesteps AEC, turn-taking, and
streaming latency — while **client tools** mean we don't give up the thing that
makes Jarvis *Jarvis*: Claude orchestrating real actions on the local machine.

## Capabilities verified against ElevenLabs docs (2026-06-15)

| Pillar | Status | Notes |
|---|---|---|
| Claude as the agent LLM | ✅ Confirmed | Anthropic models (Claude Sonnet 4, 3.7 Sonnet) selectable natively in LLM settings. Custom LLM endpoint (proxy → Anthropic API) available as an escape hatch. |
| Local execution via client tools | ✅ Confirmed | Client tools run locally via the SDK, registered in code. Python is first-class (`ClientTools().register(...)`). **No public webhook/tunnel needed** — run the SDK on the machine to control. |
| Barge-in / turn-taking | ✅ Confirmed | Turn-taking model (Eager/Normal/Patient) + silence threshold. `interruption` is a subscribable client event, so the local code is notified on barge-in. |
| Interrupt vs **in-flight action** | ✅ **Confirmed (spike, 2026-06-29)** | The SDK does **not** cancel a running client tool on barge-in or "stop" — it runs to completion and still returns its result. `handle_interruption()` only flushes buffered audio. Cancellation is entirely our job, and must be LLM-driven. See "Spike results" below. |

Sources:
- Models / LLM settings — https://elevenlabs.io/docs/agents-platform/customization/llm
- Claude Sonnet 4 in ElevenLabs — https://elevenlabs.io/blog/claude-sonnet-4-is-now-available-in-conversational-ai
- Client tools — https://elevenlabs.io/docs/eleven-agents/customization/tools/client-tools
- Conversation flow (turn-taking & interruptions) — https://elevenlabs.io/docs/eleven-agents/customization/conversation-flow
- Python SDK — https://elevenlabs.io/docs/conversational-ai/libraries/python

## Design decisions

### One brain, not two
Claude is the agent's LLM (native ElevenLabs option to start). It handles
conversation *and* emits action tool calls. We deliberately avoid a two-brain
split (ElevenLabs' default LLM for chat + a separate Claude for actions) — that
adds a hand-off, latency, and two prompts to maintain.

### Actions are not uniform
- **Instant + irreversible** (`open_app`): done before a "stop" can land; cancel
  is moot, at most offer a compensating action.
- **Composite / long-running** (`open_work_environment`): the interesting case —
  see interruption policy below.
- **Reversible** (`set_volume`): just don't apply, or let the user correct.
- **Consequential / external** (`send_email`, smart-home `unlock_door`): never
  fire optimistically — confirm *before* acting (two-phase, below).

### Interruption policy
1. **Pause-and-report, not auto-rollback.** On cancelling a composite action,
   stop issuing further steps and report progress ("opened VSCode and Slack
   before you stopped me — finish, leave it, or close them?"). Surprise undo is
   worse than a known half-state. Reserve rollback for cheap/safe reversals.
2. **Two-phase for consequential actions.** Announce intent, pause a beat, then
   execute — so barge-in during the announcement cancels cleanly *before*
   anything happens.
3. **Classify the interruption; don't blind-abort.** A barge-in may be a
   **cancel** ("stop, wrong thing"), an **augment** ("also open Notion"), or
   **chatter**. Let Claude classify intent — only cancel/correct should touch the
   executor.

### Executor primitives needed
- **Cancellable tasks** — run long actions as cancellable async tasks with a
  cancel token, never blocking calls.
- **Cancel channel** — translate the `interruption` client event into "cancel
  the in-flight task." (Exact behavior pending the spike above.)
- **Per-step checkpoints** — execute macros step-by-step recording progress, so
  on cancel we know exactly how far we got.
- **Idempotency** — `open_app` should no-op if the app is already running, so an
  interrupted-then-rerun macro doesn't double-launch.
- **Report actual state back** — the tool result must reflect *real* partial
  completion, not the intended plan, or Claude's next turn reasons on a wrong
  world state.

## Spike results (resolved 2026-06-29)
Ran a deliberately slow client tool (`slow_action`, 8s of 0.5s ticks) via a
throwaway harness (`spike_interruption.py`), barged in mid-execution, and logged
every callback with timestamps. Findings:

1. **The SDK does not cancel an in-flight client tool.** On both an explicit
   "stop" turn *and* a true over-speech barge-in, all 16 ticks ran to completion
   and the result was still returned to the agent. `handle_interruption()`
   (conversation.py) only flushes buffered *audio* via `audio_interface.interrupt()`;
   it never touches running tools and invokes no user callback.
2. **Audio-interruption and action-cancellation are unrelated channels.**
   `callback_agent_response_correction` fires *only* when the user talks over
   **active TTS**, and only truncates the spoken text. When the agent is silent
   during a long action, saying "stop" produces an ordinary user turn and **no**
   interruption event. So correction is not a usable cancel signal.
3. **The LLM will lie about cancellation.** The agent said *"No problem, I've
   stopped it"* while the tool kept running ~5 more seconds. The conversation
   layer has no knowledge of — or power over — the running action.
4. **Conversation and tools run concurrently** on separate threads (ClientTools
   uses its own ThreadPoolExecutor + event loop); the agent produced full spoken
   turns while ticks kept printing.

**Design consequence — cancellation must be LLM-driven.** Claude classifies a
"stop" as cancel intent and calls an explicit `cancel_action` client tool that
flips a cancel flag the running task polls between steps (the cancel-token
primitive above). Long tools must poll that flag **cooperatively** — a blocking
`sleep`/subprocess can't be cancelled mid-call. The tool result must report
*real* partial progress so the agent stops claiming false completions.

**Implemented (Stage 4).** `app/cancellation.py` holds a `CancelToken` and a
single "current operation" slot (`begin()`/`current()`/`end()`, guarded by a
lock). `cancel_action` in `app/tools.py` reads the current token, cancels it,
waits for it to actually stop, and returns the truthful partial-progress string
— `cancel_action` deliberately blocks on the stop so the result it hands back is
the agent's source of truth (it can't speak until the result returns). Verified
live: "stop" mid-`slow_action` halted it at tick 7 and the agent said "Stopped
after seven of sixteen steps." — the exact inverse of the failure above. Limits:
single in-flight action only (concurrent actions need a `tool_call_id`-keyed
registry — `begin()` warns when the limit is exceeded). No longer dormant as of
Stage 5: `run_macro` (`app/macros.py`) is the first real cancel-token consumer —
its run-loop polls `token.cancelled` between app launches and keeps
`token.set_progress()` a speakable cumulative summary for `cancel_action`.

## Impact on the old roadmap
This pivot obsoletes several previously planned stages:
- **Whisper STT** — no longer needed (ElevenLabs does STT).
- **Local TTS endpoint / pyttsx3** — replaced by ElevenLabs TTS.
- **WebSocket refactor** — handled by the ElevenLabs SDK.
- **Wake word (Porcupine)** — re-evaluate; ElevenLabs may cover activation.

The Stage 1 `/chat` endpoint + `SessionStore` work is not wasted: it can be
repurposed as the **custom-LLM proxy endpoint** if/when we outgrow the native
Claude option, or kept as a text-only fallback interface.
