# Design: Jarvis web UI — action-capable chat with memory

Date: 2026-06-30
Stage: 8 (user-facing app), scoped down to a **single-user personal** assistant
Status: Approved design, pre-implementation

## Background

Jarvis today is two disconnected surfaces: a text `POST /jarvis/chat` endpoint
that only *converses* (single Claude call, no tools, in-memory history), and a
standalone voice loop (`app/voice.py`) that *acts* (executes `open_app` /
`run_macro` / `cancel_action` as ElevenLabs client tools on-device). There is no
UI, and nothing persists across restarts.

This sub-project gives Jarvis a **working face**: one web page where the user can
**type or talk**, and Jarvis **acts** (opens apps, runs macros) and **remembers**
(persisted conversations + cross-session memory). It is deliberately scoped to a
**single user on their own machine** — the multi-user / auth / observability
ambitions of the full Stage 8 roadmap are out of scope (see "Future work").

## Decisions (from brainstorming)

- **Interaction:** one page, type **or** talk. Voice uses the **browser Web Speech
  API** (`SpeechRecognition` for input, `SpeechSynthesis` for output) — *not* the
  ElevenLabs widget. The polished ElevenLabs loop (`app/voice.py`) is left
  untouched as a separate path. Rationale: a browser tab is sandboxed and cannot
  open OS apps, so the widget would need a localhost execution bridge; Web Speech
  feeding the same server-side `/chat` keeps **one brain for typing and talking**
  with zero extra services. (Brainstorm approach "B".)
- **Actions:** `/chat` gains a Claude **tool-use loop** that executes tools
  **server-side** (the server runs on the user's machine, so "server-side" = "on
  this machine"). The existing `app/tools.py` functions take a dict and return a
  string, so they are reused directly as the tool dispatch.
- **Memory = both** persistent conversations and cross-session recall:
  - **Persistent conversations** in SQLite, replacing the in-memory `SessionStore`
    behind the same interface.
  - **Cross-session memory** via a new **`remember` tool** Jarvis calls when it
    learns a durable fact; facts are stored in SQLite and injected into the system
    prompt every turn. (Mirrors how Claude Code's own memory works — the model
    decides what to keep, rather than a second summarization call per turn.)
- **Frontend:** a single **vanilla HTML/JS/CSS** page served by FastAPI — no build
  step (a deliberate deviation from the aspirational TypeScript, to actually
  finish).
- **Persistence granularity:** persist the **user turn** and Jarvis's **final text
  reply** only — not the intermediate `tool_use`/`tool_result` blocks (transient
  per request; the reply captures the outcome).
- **Single-user / local:** no auth, bind to localhost. DB file `jarvis.db` at repo
  root, **gitignored** (user data), following the shipped `macro_store` pattern
  (new connection per call, `CREATE TABLE IF NOT EXISTS` on connect).

## Components & interfaces

### 1. `app/conversation_store.py` — persistent conversations (SQLite)
Replaces the in-memory `SessionStore`; same DI shape (`get_*` dependency).
```python
# Schema (jarvis.db):
#   conversations(id TEXT PRIMARY KEY, title TEXT, created_at TEXT, updated_at TEXT)
#   messages(id INTEGER PK AUTOINCREMENT, conversation_id TEXT, role TEXT,
#            content TEXT, created_at TEXT)   -- INDEX on conversation_id
def new_session() -> str                                  # creates a conversation, returns id
def append(session_id: str, role: str, content: str) -> None
def get(session_id: str) -> list[dict]                    # [{"role","content"}], oldest-first
def list_conversations() -> list[dict]                    # [{"id","title","updated_at"}], recent-first
```
`append` sets the conversation `title` from the first user message (truncated
~60 chars) and bumps `updated_at`. Timestamps are ISO strings written internally
(`datetime.now(timezone.utc)`); message ordering in tests relies on the
autoincrement `id`, so no time injection is needed for determinism. The API
endpoint that reopens a thread reuses `get(id)` (no separate method).

### 2. `app/memory_store.py` — cross-session memory (SQLite)
```python
# Schema (jarvis.db):  memories(id INTEGER PK AUTOINCREMENT, content TEXT, created_at TEXT)
def remember(content: str) -> None        # store a durable fact
def list_memories() -> list[str]          # all facts, oldest-first
```

### 3. `app/agent.py` — the tool-use loop (the core new logic)
```python
@dataclass
class ActionEvent:
    tool: str            # "open_app" | "run_macro" | "cancel_action" | "remember"
    input: dict
    result: str

@dataclass
class AgentResult:
    reply: str
    actions: list[ActionEvent]

def run_agent(history, user_message, *, memories=(), settings=None,
              client=None, max_steps=8) -> AgentResult
```
- Builds `system = DEFAULT_SYSTEM + memory_block(memories) + tool-use guidance`
  (the guidance tells Jarvis to call `remember` when it learns a durable fact and
  to use the action tools when asked to open things).
- `TOOLS`: Anthropic tool definitions (`name`, `description`, `input_schema`) for
  `open_app`, `run_macro`, `cancel_action`, `remember`. (These schemas previously
  lived only in the ElevenLabs dashboard; now they live in Python for the API
  path.)
- `DISPATCH`: `{name: callable}` — `open_app`/`run_macro`/`cancel_action` from
  `app/tools.py`; `remember` wraps `memory_store.remember`.
- Loop: call `client.messages.create(model, system, tools=TOOLS, messages=...)`;
  while `stop_reason == "tool_use"` and step < `max_steps`: for each `tool_use`
  block, `result = DISPATCH[name](input)` (unknown tool / exception → an error
  string as the `tool_result`, so Claude can recover), record an `ActionEvent`,
  append the assistant block + a `user` `tool_result` block, re-call. Return the
  final text + the collected `actions`. Hitting `max_steps` returns whatever text
  exists plus a note (guards against a tool-call loop).

### 4. `app/main.py` — endpoints
- `POST /jarvis/chat` — `session_id = req.session_id or store.new_session()`;
  `result = run_agent(store.get(session_id), req.message, memories=memory_store.list_memories(), ...)`;
  persist the user turn and `result.reply`; return `ChatResponse` (now with
  `actions`). Existing `anthropic` error → `HTTPException` handling kept.
- `GET /jarvis/conversations` → `list_conversations()`.
- `GET /jarvis/conversations/{id}` → `get(id)` (404 if empty/unknown).
- `GET /jarvis/memories` → `list_memories()` (for the UI's memory panel).
- Mount the static frontend at `/` (FastAPI `StaticFiles`).

### 5. `app/schemas.py` — additions
```python
class ActionView(BaseModel):     # what the UI shows per action
    tool: str
    summary: str                 # the tool's result string

class ChatResponse(BaseModel):   # + actions
    reply: str
    session_id: str
    model: str
    input_tokens: int
    output_tokens: int
    actions: list[ActionView] = []

class ConversationSummary(BaseModel):
    id: str
    title: str
    updated_at: str

class Message(BaseModel):
    role: str
    content: str
```

### 6. `app/static/` — frontend (vanilla)
`index.html` + `app.js` + `style.css`. Layout: a left **conversation list**
(from `GET /conversations`, click to reopen via `GET /conversations/{id}`), a main
**transcript**, a text input + send button, and a **mic button** (Web Speech;
hidden if unsupported). Replies render in the transcript, are **spoken** via
`SpeechSynthesis`, and any `actions[]` render as small **chips** ("Opened
PyCharm; Slack already running"). A small **"🧠 remembers"** panel
(`GET /memories`) is a stretch — facts are injected server-side regardless.

## Data flow

```
type ──┐
       ├─► POST /jarvis/chat {message, session_id?}
talk ──┘   (browser Web Speech → text)
              │
              ├─ memories = memory_store.list_memories()
              ├─ result = run_agent(store.get(sid), message, memories=…)
              │     └─ Claude ⇄ tools:  open_app / run_macro / cancel_action / remember
              │            (executed server-side = this machine)
              ├─ store.append(sid, "user", message); store.append(sid, "assistant", result.reply)
              └─► {reply, session_id, actions[], tokens} ─► render + SpeechSynthesis + action chips
```

## Edge cases & error handling

| Situation | Behavior |
|---|---|
| Unknown tool name / tool raises | `tool_result` = error string; Claude recovers and replies |
| Tool-call loop | `max_steps` (8) cap; return text-so-far + a note |
| `run_macro` cancel mid-run (HTTP) | a concurrent `/chat` saying "stop" runs in FastAPI's threadpool → `cancel_action` flips the shared token (same two-thread model as the voice spike). Supported but edge; not a primary flow |
| Web Speech unsupported (non-Chrome) | mic button hidden; typing still works |
| Empty memory | no memory block in the system prompt |
| Unknown / empty conversation id | `GET /conversations/{id}` → 404 |
| Anthropic API error | existing `HTTPException` mapping (status passthrough / 503) |

## Trust boundary

`/chat` executes real OS actions on the user's machine. Mitigations matching the
personal-app scope: server **binds to localhost**, tools are a **fixed allowlist**
(open app / run macro / cancel / remember — not arbitrary shell), and a
prompt-injected "open X" can at worst open an installed app or run a saved macro
(small blast radius). Documented, not a security sub-project. Multi-user + real
authz is Stage 8.

## Testing

- **`tests/test_conversation_store.py`** (temp `jarvis.db` via `tmp_path`):
  `new_session` + `append` + `get` round-trip; `list_conversations` ordering +
  title from first user message; `get` of unknown id is empty.
- **`tests/test_memory_store.py`**: `remember` + `list_memories` round-trip;
  ordering.
- **`tests/test_agent.py`** (fake Anthropic client scripted to return a `tool_use`
  block then text): the tool is dispatched, its `tool_result` is threaded back, the
  final text + `ActionEvent`s are returned; unknown-tool/exception path yields an
  error `tool_result` not a crash; `max_steps` cap terminates a tool loop; the
  `remember` tool persists a fact that then appears in the next system prompt.
- **`tests/test_chat_endpoint.py`** (fake client + fake tools): `/chat` persists
  the turn and returns `actions`; continuing with a `session_id` replays history.
- **Frontend:** manual acceptance (vanilla, no framework): type a message → reply
  renders + is spoken; "open my work environment" → action chips + apps open; mic
  button transcribes; reopen a past conversation from the list; restart the server
  → conversations + memory survive.

## Future work (explicitly out of scope here)

- **Stage 8 proper:** multi-user, auth/authz, a `users` table, per-user isolation,
  observability (token/cost/latency persisted), eval harness.
- **ElevenLabs widget in-browser** (brainstorm approach "A") with a localhost tool
  bridge, if browser voice quality becomes the point.
- **Memory management:** `forget`/edit, dedup, and summarization when the fact list
  grows large (inject-all is fine at personal scale).
- **Streaming** responses; unifying `macros.db` into `jarvis.db`.
