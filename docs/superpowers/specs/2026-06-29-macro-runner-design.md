# Design: macro storage + cancellable runner (`run_macro`)

Date: 2026-06-29
Stage: 5 (composite actions / macros) — sub-project #1 of 3
Status: Approved design, pre-implementation

## Background

Stage 5 is a configurable **macro system**: named groups of apps the user can
open by voice ("open my work environment"). It's the first real consumer of the
Stage 4 cancel token (`app/cancellation.py`, `cancel_action`).

The full vision spans three subsystems with a clear dependency order:

1. **Macro storage + cancellable runner** — *this spec*. Persistence + the voice
   tool that runs a macro cancellably. Self-contained; testable via voice with
   seeded macros.
2. **Backend management API** — FastAPI endpoints to list installed apps and
   CRUD macros. Depends on #1's storage.
3. **Frontend UI** — TypeScript tab to manage macros. Depends on #2.

This spec covers **#1 only**. #2 and #3 get their own spec → plan → build cycles.

## Decisions (from brainstorming)

- **Scope:** configurable macro system (not a single hardcoded macro), but #1
  builds storage + runner; the management API/UI are later sub-projects.
- **Storage:** SQLite, behind a small `macro_store` interface (the runner never
  sees SQL). This is the stack's "SQLite when needed" moment, justified by the
  future CRUD API.
- **Architecture:** Approach A — a dedicated `app/macros.py` orchestration module
  composing `macro_store` + `launcher`; the `run_macro` client tool is a thin
  wrapper.
- **Idempotency:** hybrid — within-session tracking (reliable core) + best-effort
  process-check (`launcher.is_running`), **biased to launch when unsure** (a
  duplicate window is better than a silently-skipped app). Within-session uses a
  **recency window** (~120s), not a permanent set, to avoid stale wrong-skips.
- **Launch result:** small refactor — `launcher.launch()` returns
  `LaunchResult(ok, message)` instead of a bare string, so the runner gets a
  machine-readable success signal instead of parsing user-facing text.
- **Cancellation:** reuse the Stage 4 token (`begin`/`current`/`end`); poll
  between apps; pause-and-report (no rollback).

## Components & interfaces

### 1. `app/macro_store.py` — persistence (SQLite behind an interface)
```python
# Schema: macros(name TEXT PRIMARY KEY, apps TEXT NOT NULL)  -- apps = JSON list
def get_macro(name: str) -> list[str] | None        # apps for an exact name, or None
def list_macros() -> dict[str, list[str]]            # all macros
def upsert_macro(name: str, apps: list[str]) -> None # create/update (seeding now; API later)
```
New SQLite connection per call (connections aren't thread-safe; the runner
executes on a worker thread). DB file `macros.db` at repo root, **gitignored**
(user data). `delete_macro` deferred to sub-project #2.

### 2. `WindowsLauncher.is_running(name: str) -> bool` — new method
Resolves `name` to its best app match (same matching as `launch`), then queries
`Get-Process` for a confident window-title/process match. **Returns `False` when
unsure** so the runner launches rather than wrongly skips. All Windows/PowerShell
coupling stays in the launcher.

### 3. `LaunchResult` + refactored `launch` (in `app/launcher.py`)
```python
@dataclass
class LaunchResult:
    ok: bool
    message: str        # user-facing string, e.g. "Opening Google Chrome."

def launch(app) -> LaunchResult     # was: -> str
```
`open_app` becomes `return launch(app).message` (one-line change). Existing
`tests/test_launcher.py` updated to assert on `.ok`/`.message`.

### 4. `app/macros.py` — orchestration (pure logic, OS-agnostic)
```python
def run(name, *, store=macro_store, launcher=None, now=time.monotonic) -> str
```
Composes `macro_store` + the `launcher` interface. Owns the cancellable run-loop,
within-session recency tracking, and the truthful summary. The injectable seams
exist for testing with fakes: `store` defaults to the `macro_store` module (any
object with `get_macro`/`list_macros` works); `launcher` defaults to `None` and
is resolved to `get_launcher()` **inside** the function (a default arg can't bind
the lazily-created singleton at import time); `now` defaults to `time.monotonic`.
`recently_launched` is a **module-level `dict[str, float]`** (app → launch time)
in `app/macros.py`, pruned against the recency window on each check. Depends on
nothing SDK- or SQL-specific.

### 5. `run_macro(params)` in `app/tools.py` — client tool (thin wrapper)
```python
def run_macro(params):
    return macros.run((params or {}).get("macro", "").strip())
```
Registered in `build_client_tools()` as `"run_macro"`.

## Data flow

```
User: "open my work environment"
  └─ agent calls run_macro(macro="work")
        └─ tools.run_macro → macros.run("work")
              ├─ store.list_macros() → fuzzy-match "work" (difflib, like open_app)
              │     └─ no match → "I don't have a macro called work. You have: dev, gaming."
              ├─ token = begin()
              ├─ for each app in the macro:
              │     ├─ token.cancelled?       → break (cancellation poll point)
              │     ├─ should_skip(app)?      → record skipped, continue
              │     ├─ launcher.launch(app)   → record opened / not-found (by .ok)
              │     │     └─ if ok: record recently_launched[app] = now()
              │     └─ token.set_progress(cumulative summary so far)
              ├─ finally: token.mark_stopped(); end(token)
              └─ return truthful summary
```

### The `should_skip(app)` decision (idempotency hybrid)
```
skip if  launcher.is_running(app)             # apps open BEFORE the macro (biased to False)
      OR recently_launched(app, within ~120s) # apps we just launched, not yet window-visible
```
The recency window covers the gap where a just-launched app hasn't drawn a window
(so `is_running` can't see it) — the interrupted-then-rerun case. The window
(not a permanent set) prevents stale wrong-skips on a much-later rerun.

## Edge cases & cancellation reporting

Each app lands in **opened / skipped (already running) / not-found**; the summary
is built from those plus cancellation state.

| Situation | Behavior |
|---|---|
| Unknown macro name | `"I don't have a macro called X. You have: dev, gaming."` |
| Macro exists but empty | `"The work macro has no apps in it."` |
| An app in the macro isn't found | record not-found, **keep going**, surface in summary |
| Everything already open | `"Everything in work is already open."` |
| Normal completion | `"Opened VSCode, Slack, and Chrome. Spotify was already running."` |
| Cancelled mid-sequence | `"Opened VSCode and Slack, then stopped — 2 of 4."` |

**Cancellation integration:** `run_macro` reuses the Stage 4 token. On "stop" the
agent calls `cancel_action`, which flips the flag; the run-loop breaks at the next
poll; `cancel_action` returns `"Stopped. {token.progress}"`. Therefore
`token.set_progress()` must hold a **cumulative human summary** after each step
(e.g. `"Opened VSCode and Slack (2 of 4)"`) — that string is what the agent speaks
on cancel. `run_macro`'s own return is its full summary; the agent answers the
cancel turn from `cancel_action`'s result (same two-results timing as the spike).
The two tools run on separate threads (spike-proven), so this works without
deadlock.

## Testing

`macros.run` takes injectable seams (`store`, `launcher`, `now`) so the run-loop,
idempotency, and cancellation are tested deterministically with fakes.

- **`tests/test_macro_store.py`** (temp SQLite via `tmp_path`): `upsert` +
  `get_macro` round-trip; `list_macros` returns all; unknown name → `None`;
  upsert overwrites an existing name.
- **`tests/test_macros.py`** (FakeLauncher + FakeStore):
  - Happy path: 3 apps, none running → all launched, summary lists all.
  - Skip already-running: `is_running` True for one → skipped, summary notes it.
  - Not-found app: `launch` returns `ok=False` → not-found, others still launch.
  - Unknown macro → helpful error; empty macro → "no apps".
  - Cancel mid-macro: `FakeLauncher.launch` calls `cancellation.current().cancel()`
    on its 2nd call → loop breaks, summary "stopped after 2", `token.progress`
    holds the cumulative summary.
  - Recency window: fresh `recently_launched` timestamp (via injected `now`) →
    skipped; expired → launched. No real waiting.
- **`tests/test_launcher.py`** (updated): assert `launch()` returns
  `LaunchResult(.ok/.message)`; add `is_running` test (mock `Get-Process`
  subprocess, assert biases to `False` on no confident match).
- **`run_macro` tool:** unpacks `params["macro"]`, delegates to `macros.run`, and
  is registered in `build_client_tools()` (`"run_macro" in tools.tools`).
- **Manual live acceptance:** seed a macro, `python -m app.voice`, say "open my
  work environment" then "stop" mid-sequence — apps open one-by-one, "stop" halts
  early, agent truthfully reports what opened.

## Dashboard & prompt wiring

Dashboard — new client tool `run_macro`:
- Type: Client tool; Name: `run_macro` (matches the `register` string).
- Description: "Run a saved macro that opens a group of apps. Use when the user
  asks to open or start a named environment/setup (e.g. 'open my work
  environment', 'start my gaming setup')."
- **Wait for response: On.**
- **Response timeout: ≥ 30s** (a macro launching several apps runs many seconds;
  the agent must not give up mid-macro).
- **Parameter:** `macro` — string, required — "The name of the macro to run, as
  the user referred to it (e.g. 'work', 'gaming')."

Prompt — add:
```
When the user asks to open a named environment, setup, or group of apps
(e.g. "open my work environment", "start my gaming setup"), call run_macro
with the macro name they used. Report exactly what the result says — which
apps opened, which were already running, which couldn't be found. If it says
there's no such macro, tell them the names it lists.
```
Cancellation needs no new prompt — the existing `cancel_action` rule covers
stopping a macro. The `macro` **parameter must be declared in the dashboard**, not
just named in the prompt (the agent can only send arguments the schema defines).

## Future work (sub-projects #2 and #3)

- **#2 Backend API:** FastAPI endpoints — `GET /apps` (installed apps, exposes the
  launcher's list), `GET/POST/PUT/DELETE /macros` (CRUD via `macro_store`, which
  gains `delete_macro`).
- **#3 Frontend:** TypeScript tab — list installed apps, create/edit/delete macros.
- **Concurrency:** if a macro and another cancellable action ever run at once, the
  single-slot cancel token is exceeded — `begin()` already warns; upgrade to a
  `tool_call_id`-keyed registry then.
