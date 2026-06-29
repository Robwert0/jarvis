# Macro Runner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A configurable, cancellable macro runner — the user says "open my work environment" and the agent opens a saved group of apps one-by-one, stoppable mid-sequence, reporting truthfully what happened.

**Architecture:** A SQLite-backed `macro_store` (behind a small interface), a `macros.py` orchestration module that runs a macro cancellably (reusing the Stage 4 cancel token), composing the existing `launcher`. A thin `run_macro` client tool exposes it. `launcher.launch()` is refactored to return `LaunchResult(ok, message)` and gains `is_running()`.

**Tech Stack:** Python 3.12, `sqlite3` (stdlib), `threading`/cancel token (Stage 4), pytest, ElevenLabs client tools.

## Global Constraints

- Virtual env at `.venv/`; run tests with `.venv/bin/python -m pytest`.
- Conventional Commits; **no AI attribution footers** (`.claude/rules/GIT_RULES.md`).
- Branch: `feature/macro-runner` (already created).
- Idempotency hybrid: skip an app if `launcher.is_running(app)` OR it was launched within `RECENCY_WINDOW = 120.0` seconds; **bias to launch when unsure** (`is_running` returns `False` on no confident match).
- Cancellation reuses the Stage 4 token (`app/cancellation.py`): poll `token.cancelled` between apps; keep `token.set_progress()` a speakable cumulative summary; `mark_stopped()`/`end()` in a `finally`.
- `macros.py` stays OS-agnostic and SQL-agnostic — reaches the DB and OS only through the `store` and `launcher` interfaces (injectable seams for tests).
- DB file `macros.db` at repo root, **gitignored**.

---

### Task 1: Macro storage (`app/macro_store.py`)

**Files:**
- Create: `app/macro_store.py`
- Test: `tests/test_macro_store.py`
- Modify: `.gitignore` (add `macros.db`)

**Interfaces — Produces:**
- `get_macro(name: str) -> list[str] | None`
- `list_macros() -> dict[str, list[str]]`
- `upsert_macro(name: str, apps: list[str]) -> None`
- Module attribute `DB_PATH` (tests monkeypatch it to a temp file).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_macro_store.py
import pytest

import app.macro_store as store


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "macros.db")


def test_upsert_and_get_roundtrip():
    store.upsert_macro("work", ["Visual Studio Code", "Slack"])
    assert store.get_macro("work") == ["Visual Studio Code", "Slack"]


def test_get_unknown_returns_none():
    assert store.get_macro("nope") is None


def test_list_macros_returns_all():
    store.upsert_macro("work", ["Code"])
    store.upsert_macro("game", ["Steam"])
    assert store.list_macros() == {"work": ["Code"], "game": ["Steam"]}


def test_upsert_overwrites_existing_name():
    store.upsert_macro("work", ["Code"])
    store.upsert_macro("work", ["Code", "Slack"])
    assert store.get_macro("work") == ["Code", "Slack"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_macro_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.macro_store'`.

- [ ] **Step 3: Write the implementation**

```python
# app/macro_store.py
import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "macros.db"


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS macros (name TEXT PRIMARY KEY, apps TEXT NOT NULL)"
    )
    return conn


def get_macro(name):
    with _connect() as conn:
        row = conn.execute(
            "SELECT apps FROM macros WHERE name = ?", (name,)
        ).fetchone()
    return json.loads(row[0]) if row else None


def list_macros():
    with _connect() as conn:
        rows = conn.execute("SELECT name, apps FROM macros").fetchall()
    return {name: json.loads(apps) for name, apps in rows}


def upsert_macro(name, apps):
    with _connect() as conn:
        conn.execute(
            "INSERT INTO macros (name, apps) VALUES (?, ?) "
            "ON CONFLICT(name) DO UPDATE SET apps = excluded.apps",
            (name, json.dumps(apps)),
        )
        conn.commit()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_macro_store.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Gitignore the DB and commit**

Add to `.gitignore` under a new line:
```
# Macro store (user data)
macros.db
```
```bash
git add app/macro_store.py tests/test_macro_store.py .gitignore
git commit -m "feat(macro): add SQLite-backed macro store"
```

---

### Task 2: `LaunchResult` refactor + `is_running` (`app/launcher.py`)

**Files:**
- Modify: `app/launcher.py`
- Modify: `app/tools.py` (`open_app` returns `.message`)
- Test: `tests/test_launcher.py` (update existing assertions + add `is_running` tests)

**Interfaces — Produces:**
- `LaunchResult` dataclass: `.ok: bool`, `.message: str`
- `WindowsLauncher.launch(name) -> LaunchResult` (was `-> str`)
- `WindowsLauncher.is_running(name) -> bool`
- `WindowsLauncher._resolve(name) -> tuple[str, str] | None` (display_name, appid)
- Module `launch(app) -> LaunchResult`, `is_running(app) -> bool`

**Interfaces — Consumes:** nothing new.

- [ ] **Step 1: Update existing launcher tests to expect `LaunchResult`, and extend the fake for `Get-Process`**

In `tests/test_launcher.py`, extend `FakeRun.__call__` to handle `Get-Process` and change the four `launch`/top-level assertions:

```python
# In FakeRun.__init__, add:
        self.window_titles: list[str] = []   # MainWindowTitle lines Get-Process returns

# In FakeRun.__call__, add a branch BEFORE the launch fallback:
        if "Get-Process" in joined:
            return SimpleNamespace(
                stdout="\n".join(self.window_titles), returncode=0, stderr=""
            )
```

Change the launch assertions:
```python
def test_launch_substring_match(fake_run: FakeRun) -> None:
    result = launcher.WindowsLauncher().launch("photos")
    assert result.ok is True
    assert result.message == "Opening Photos."
    assert APPS[0]["AppID"] in fake_run.launch_commands[0]


def test_launch_fuzzy_match(fake_run: FakeRun) -> None:
    result = launcher.WindowsLauncher().launch("calculater")
    assert result.ok is True
    assert result.message == "Opening Calculator."
    assert APPS[1]["AppID"] in fake_run.launch_commands[0]


def test_launch_no_match_does_not_launch(fake_run: FakeRun) -> None:
    result = launcher.WindowsLauncher().launch("zzz")
    assert result.ok is False
    assert result.message.startswith("I couldn't find an app called zzz")
    assert fake_run.launch_commands == []


def test_launch_reports_powershell_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = FakeRun(returncode=1, stderr="boom")
    monkeypatch.setattr(launcher.subprocess, "run", runner)
    result = launcher.WindowsLauncher().launch("photos")
    assert result.ok is False
    assert result.message == "I couldn't open photos - boom."


def test_launch_unsupported_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(launcher, "detect_platform", lambda: "linux")
    result = launcher.launch("photos")
    assert result.ok is False
    assert result.message == "Opening apps isn't wired up on this platform yet."
```

Add `is_running` tests:
```python
def test_is_running_true_when_window_title_matches(fake_run: FakeRun) -> None:
    fake_run.window_titles = ["index.js - Google Chrome", "Settings"]
    assert launcher.WindowsLauncher().is_running("chrome") is True


def test_is_running_false_when_no_match(fake_run: FakeRun) -> None:
    fake_run.window_titles = ["Settings"]
    assert launcher.WindowsLauncher().is_running("chrome") is False


def test_is_running_false_when_app_unknown(fake_run: FakeRun) -> None:
    # name resolves to nothing -> biased to False (so caller launches)
    assert launcher.WindowsLauncher().is_running("zzz") is False


def test_top_level_is_running_unsupported_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(launcher, "detect_platform", lambda: "linux")
    assert launcher.is_running("photos") is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_launcher.py -v`
Expected: FAIL — `AttributeError`/assertion errors (`result` is a str, has no `.ok`; `is_running` undefined).

- [ ] **Step 3: Refactor `launcher.py`**

Add the dataclass at the top (after imports):
```python
from dataclasses import dataclass


@dataclass
class LaunchResult:
    ok: bool
    message: str
```

Replace `WindowsLauncher.launch` with a `_resolve` helper + a `LaunchResult`-returning `launch`, and add `is_running`:
```python
    def _resolve(self, name):
        """Best-match (display_name, appid) for a name, or None."""
        apps = self._installed_apps()
        app_name = name.strip().lower()
        hits = [(n, a) for n, a in apps if app_name in n.lower()]
        if hits:
            return min(hits, key=lambda pair: len(pair[0]))
        by_lower = {n.lower(): (n, a) for n, a in apps}
        close = difflib.get_close_matches(app_name, list(by_lower), n=1, cutoff=0.6)
        if close:
            return by_lower[close[0]]
        return None

    def launch(self, name):
        app_name = name.strip().lower()
        resolved = self._resolve(name)
        if resolved is None:
            apps = self._installed_apps()
            by_lower = {n.lower(): (n, a) for n, a in apps}
            suggestions = difflib.get_close_matches(
                app_name, list(by_lower), n=3, cutoff=0.4
            )
            hint = f"Did you mean: {', '.join(suggestions)}?" if suggestions else " "
            return LaunchResult(
                False, f"I couldn't find an app called {app_name}. {hint}"
            )
        display_name, appid = resolved
        res = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                f'Start-Process "shell:AppsFolder\\{appid}"',
            ],
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            return LaunchResult(True, f"Opening {display_name}.")
        return LaunchResult(False, f"I couldn't open {app_name} - {res.stderr.strip()}.")

    def is_running(self, name):
        resolved = self._resolve(name)
        if resolved is None:
            return False
        display_name, _ = resolved
        res = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "Get-Process | Where-Object { $_.MainWindowTitle } | "
                "Select-Object -ExpandProperty MainWindowTitle",
            ],
            capture_output=True,
            text=True,
        )
        return display_name.lower() in res.stdout.lower()
```

Update the module-level functions:
```python
def launch(app):
    launcher = get_launcher()
    if launcher is None:
        return LaunchResult(False, "Opening apps isn't wired up on this platform yet.")
    return launcher.launch(app)


def is_running(app):
    launcher = get_launcher()
    if launcher is None:
        return False
    return launcher.is_running(app)
```

In `app/tools.py`, change `open_app`'s last line:
```python
    return launch(app).message
```

- [ ] **Step 4: Run the full suite to verify pass**

Run: `.venv/bin/python -m pytest -q`
Expected: all pass (launcher tests updated, `open_app`/cancel tests still green).

- [ ] **Step 5: Commit**

```bash
git add app/launcher.py app/tools.py tests/test_launcher.py
git commit -m "refactor(launcher): return LaunchResult and add is_running for the macro runner"
```

---

### Task 3: Macro runner (`app/macros.py`)

**Files:**
- Create: `app/macros.py`
- Test: `tests/test_macros.py`

**Interfaces — Consumes:** `macro_store.{get_macro,list_macros}` (Task 1); `launcher.get_launcher`, `LaunchResult`, the launcher's `.launch(app) -> LaunchResult` and `.is_running(app) -> bool` (Task 2); `cancellation.{begin,current,end}` (Stage 4).

**Interfaces — Produces:**
- `run(name, *, store=macro_store, launcher=None, now=time.monotonic) -> str`
- Module dict `_recently_launched: dict[str, float]`
- `RECENCY_WINDOW = 120.0`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_macros.py
import pytest

import app.cancellation as c
import app.macros as macros
from app.launcher import LaunchResult


@pytest.fixture(autouse=True)
def reset_state():
    c._current = None
    macros._recently_launched.clear()
    yield
    c._current = None
    macros._recently_launched.clear()


class FakeStore:
    def __init__(self, data):
        self._data = data

    def list_macros(self):
        return dict(self._data)

    def get_macro(self, name):
        return self._data.get(name)


class FakeLauncher:
    def __init__(self, running=(), fail=(), cancel_after=None):
        self.running = set(running)
        self.fail = set(fail)
        self.cancel_after = cancel_after
        self.launched = []

    def is_running(self, app):
        return app in self.running

    def launch(self, app):
        self.launched.append(app)
        if self.cancel_after and len(self.launched) >= self.cancel_after:
            c.current().cancel()
        ok = app not in self.fail
        return LaunchResult(ok, f"Opening {app}." if ok else f"couldn't find {app}")


def run(name, store, launcher, now=lambda: 1000.0):
    return macros.run(name, store=store, launcher=launcher, now=now)


def test_happy_path_launches_all():
    fl = FakeLauncher()
    summary = run("work", FakeStore({"work": ["Code", "Slack", "Chrome"]}), fl)
    assert fl.launched == ["Code", "Slack", "Chrome"]
    assert "opened" in summary.lower()
    assert "Code" in summary and "Slack" in summary and "Chrome" in summary


def test_skips_already_running():
    fl = FakeLauncher(running=["Slack"])
    summary = run("work", FakeStore({"work": ["Code", "Slack"]}), fl)
    assert fl.launched == ["Code"]            # Slack skipped
    assert "already running" in summary.lower()
    assert "Slack" in summary


def test_not_found_app_does_not_abort_rest():
    fl = FakeLauncher(fail=["Spotofy"])
    summary = run("work", FakeStore({"work": ["Spotofy", "Code"]}), fl)
    assert fl.launched == ["Spotofy", "Code"]  # attempted both
    assert "couldn't find" in summary.lower()
    assert "Code" in summary


def test_unknown_macro_lists_available():
    summary = run("zzz", FakeStore({"work": ["Code"], "game": ["Steam"]}), FakeLauncher())
    assert "work" in summary and "game" in summary


def test_empty_macro():
    summary = run("work", FakeStore({"work": []}), FakeLauncher())
    assert "no apps" in summary.lower()


def test_cancel_mid_macro_stops_and_reports_progress():
    fl = FakeLauncher(cancel_after=2)
    summary = run("work", FakeStore({"work": ["Code", "Slack", "Chrome"]}), fl)
    assert fl.launched == ["Code", "Slack"]    # Chrome never launched
    assert "stopped" in summary.lower()
    # token.progress carries the speakable cumulative summary for cancel_action
    # (token is cleared by end(); assert via the returned summary instead)
    assert "Code" in summary and "Slack" in summary


def test_recency_window_skips_recently_launched():
    macros._recently_launched["Code"] = 1000.0           # "launched now"
    fl = FakeLauncher()
    summary = run("work", FakeStore({"work": ["Code"]}), fl, now=lambda: 1050.0)  # 50s later
    assert fl.launched == []                              # within 120s window -> skipped
    assert "already running" in summary.lower() or "Code" in summary


def test_recency_window_expired_relaunches():
    macros._recently_launched["Code"] = 1000.0
    fl = FakeLauncher()
    run("work", FakeStore({"work": ["Code"]}), fl, now=lambda: 1200.0)  # 200s later (> 120)
    assert fl.launched == ["Code"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_macros.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.macros'`.

- [ ] **Step 3: Write the implementation**

```python
# app/macros.py
import difflib
import time

from app import macro_store
from app.cancellation import begin, end
from app.launcher import get_launcher

RECENCY_WINDOW = 120.0
_recently_launched = {}    # app name -> monotonic launch time


def _join(names):
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def _summary(opened, skipped, not_found):
    parts = []
    if opened:
        parts.append("opened " + _join(opened))
    if skipped:
        parts.append(_join(skipped) + " already running")
    if not_found:
        parts.append("couldn't find " + _join(not_found))
    return "; ".join(parts) if parts else "nothing to do"


def _match(name, macros):
    key = name.strip().lower()
    hits = [m for m in macros if key in m.lower()]
    if hits:
        return min(hits, key=len)
    by_lower = {m.lower(): m for m in macros}
    close = difflib.get_close_matches(key, list(by_lower), n=1, cutoff=0.6)
    return by_lower[close[0]] if close else None


def _recently(app, now):
    ts = _recently_launched.get(app)
    return ts is not None and (now() - ts) < RECENCY_WINDOW


def run(name, *, store=macro_store, launcher=None, now=time.monotonic):
    if launcher is None:
        launcher = get_launcher()
    all_macros = store.list_macros()
    matched = _match(name, all_macros)
    if matched is None:
        names = ", ".join(all_macros) if all_macros else "none"
        return f"I don't have a macro called {name}. You have: {names}."
    apps = all_macros[matched]
    if not apps:
        return f"The {matched} macro has no apps in it."

    token = begin()
    opened, skipped, not_found = [], [], []
    try:
        for app in apps:
            if token.cancelled:
                break
            if launcher.is_running(app) or _recently(app, now):
                skipped.append(app)
            else:
                result = launcher.launch(app)
                if result.ok:
                    opened.append(app)
                    _recently_launched[app] = now()
                else:
                    not_found.append(app)
            token.set_progress(_summary(opened, skipped, not_found))
        body = _summary(opened, skipped, not_found)
        if token.cancelled:
            return f"Stopped — {body} before you stopped me."
        return body[:1].upper() + body[1:] + "."
    finally:
        token.mark_stopped()
        end(token)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_macros.py -v`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
git add app/macros.py tests/test_macros.py
git commit -m "feat(macro): add cancellable macro runner with idempotency hybrid"
```

---

### Task 4: `run_macro` client tool (`app/tools.py`)

**Files:**
- Modify: `app/tools.py`
- Test: `tests/test_tools_macro.py`

**Interfaces — Consumes:** `macros.run` (Task 3).
**Interfaces — Produces:** `run_macro(params) -> str`, registered as `"run_macro"`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_tools_macro.py
import app.tools as tools


def test_run_macro_delegates_to_macros_run(monkeypatch):
    calls = []
    monkeypatch.setattr(tools.macros, "run", lambda name: calls.append(name) or "ok")
    assert tools.run_macro({"macro": "work"}) == "ok"
    assert calls == ["work"]


def test_run_macro_strips_and_handles_missing_param(monkeypatch):
    calls = []
    monkeypatch.setattr(tools.macros, "run", lambda name: calls.append(name) or "ok")
    tools.run_macro({"macro": "  work  "})
    tools.run_macro({})
    assert calls == ["work", ""]


def test_run_macro_registered():
    assert "run_macro" in tools.build_client_tools().tools
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_tools_macro.py -v`
Expected: FAIL — `AttributeError: module 'app.tools' has no attribute 'run_macro'` (and no `tools.macros`).

- [ ] **Step 3: Write the implementation**

In `app/tools.py`, add the import and the tool, and register it:
```python
from app import macros


def run_macro(params):
    return macros.run((params or {}).get("macro", "").strip())
```
In `build_client_tools()`:
```python
    tools.register("run_macro", run_macro)
```

- [ ] **Step 4: Run the full suite**

Run: `.venv/bin/python -m pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add app/tools.py tests/test_tools_macro.py
git commit -m "feat(macro): add run_macro client tool"
```

---

### Task 5: Dashboard + prompt wiring, seed a macro, live acceptance, docs — manual

No automated test; this wires the tool to the agent and verifies end-to-end.

- [ ] **Step 1: Seed a macro for testing** (one-off, from a Python shell)

```bash
.venv/bin/python -c "from app import macro_store as s; s.upsert_macro('work', ['Visual Studio Code', 'Slack', 'Google Chrome'])"
```

- [ ] **Step 2: Dashboard — add the `run_macro` client tool**
- Type: Client tool; Name: `run_macro`.
- Description: "Run a saved macro that opens a group of apps. Use when the user asks to open or start a named environment/setup (e.g. 'open my work environment', 'start my gaming setup')."
- Wait for response: **On**.
- Response timeout: **≥ 30s**.
- Parameter: `macro` — string, **required** — "The name of the macro to run, as the user referred to it (e.g. 'work', 'gaming')."

- [ ] **Step 3: Prompt — add the macro rule** to the agent system prompt:
```
When the user asks to open a named environment, setup, or group of apps
(e.g. "open my work environment", "start my gaming setup"), call run_macro
with the macro name they used. Report exactly what the result says — which
apps opened, which were already running, which couldn't be found. If it says
there's no such macro, tell them the names it lists.
```

- [ ] **Step 4: Live acceptance** — `.venv/bin/python -m app.voice`
  - Say "open my work environment" → apps open one-by-one; agent reports what opened.
  - Run it again immediately → already-open apps are skipped (recency/`is_running`).
  - Start it, then say "stop" mid-sequence → it halts early; agent truthfully reports the partial set (via `cancel_action` + `token.progress`).

- [ ] **Step 5: Docs + commit**

Update `CLAUDE.md` (mark Stage 5 sub-project #1 done; note #2 API / #3 frontend remain) and add a one-line note to `docs/voice-architecture.md` that `run_macro` is the first cancel-token consumer.
```bash
git add CLAUDE.md docs/voice-architecture.md
git commit -m "docs(macro): mark macro runner (Stage 5 #1) done"
```

---

## Self-Review

**Spec coverage:**
- SQLite store behind interface → Task 1. ✓
- `LaunchResult` refactor + `is_running` → Task 2. ✓
- `macros.run` orchestration, fuzzy-match, idempotency hybrid (is_running + recency window), cancel poll + speakable progress, truthful summary, empty/unknown/not-found edges → Task 3. ✓
- `run_macro` thin tool + registration → Task 4. ✓
- Dashboard `macro` param + prompt + live acceptance + docs → Task 5. ✓
- Injectable seams (`store`/`launcher`/`now`) → Task 3 signature + tests. ✓
- `macros.db` gitignored → Task 1 Step 5. ✓

**Placeholder scan:** None — every code/edit step shows full content. Task 5 is manual (dashboard/voice) by nature; its steps are concrete commands/settings, not placeholders.

**Type consistency:** `LaunchResult(ok, message)`, `launch() -> LaunchResult`, `is_running() -> bool`, `_resolve() -> tuple|None`, `macros.run(name, *, store, launcher, now) -> str`, `get_macro/list_macros/upsert_macro`, `_recently_launched`, `RECENCY_WINDOW` are used identically across Tasks 1–4 and the tests. The `run_macro` tool name string matches `tools.register`. ✓
