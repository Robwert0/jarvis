# Jarvis Web UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One web page where a single user can type or talk to Jarvis and have it act (open apps, run macros) and remember (persisted conversations + cross-session memory).

**Architecture:** A SQLite layer (`conversation_store`, `memory_store`) following the shipped `macro_store` pattern; an `agent.py` tool-use loop that runs Claude with the existing `app/tools.py` functions plus a new `remember` tool; `main.py` `/chat` upgraded to drive the loop and persist turns, with conversation/memory read endpoints; a vanilla static page served by FastAPI doing text + Web Speech voice.

**Tech Stack:** Python 3.12, FastAPI, `sqlite3` (stdlib), Anthropic SDK tool use, pytest, vanilla HTML/JS/CSS (no build), browser Web Speech API.

## Global Constraints

- Virtual env at `.venv/`; run tests with `.venv/bin/python -m pytest`.
- Conventional Commits; **no AI attribution footers** (`.claude/rules/GIT_RULES.md`).
- Branch: `feature/web-ui` (already created).
- Single-user, **no auth**, server binds localhost. DB file `jarvis.db` at repo root, **gitignored**.
- Stores follow the shipped `app/macro_store.py` pattern: module-level functions, new `sqlite3` connection per call, `CREATE TABLE IF NOT EXISTS` on connect, module attribute `DB_PATH` tests monkeypatch to a temp file.
- Tools are a fixed allowlist: `open_app`, `run_macro`, `cancel_action`, `remember`. No arbitrary shell.
- Persist only the user turn and Jarvis's final text reply — never intermediate `tool_use`/`tool_result` blocks.

---

### Task 1: Conversation store (`app/conversation_store.py`)

**Files:**
- Create: `app/conversation_store.py`
- Test: `tests/test_conversation_store.py`
- Modify: `.gitignore` (add `jarvis.db`)

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `DB_PATH` (module attribute)
  - `new_session() -> str`
  - `append(session_id: str, role: str, content: str) -> None`
  - `get(session_id: str) -> list[dict]`  (`[{"role","content"}]`, oldest-first)
  - `list_conversations() -> list[dict]`  (`[{"id","title","updated_at"}]`, recent-first)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_conversation_store.py
import pytest

import app.conversation_store as store


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "jarvis.db")


def test_new_session_returns_id():
    sid = store.new_session()
    assert isinstance(sid, str) and sid


def test_append_and_get_roundtrip():
    sid = store.new_session()
    store.append(sid, "user", "hello")
    store.append(sid, "assistant", "hi there")
    assert store.get(sid) == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]


def test_get_unknown_session_is_empty():
    assert store.get("nope") == []


def test_title_comes_from_first_user_message():
    sid = store.new_session()
    store.append(sid, "user", "what's the weather like today")
    store.append(sid, "assistant", "sunny")
    convs = store.list_conversations()
    assert len(convs) == 1
    assert convs[0]["id"] == sid
    assert convs[0]["title"] == "what's the weather like today"


def test_list_conversations_recent_first():
    a = store.new_session()
    store.append(a, "user", "first")
    b = store.new_session()
    store.append(b, "user", "second")
    store.append(a, "user", "third")  # touches `a` most recently
    ids = [c["id"] for c in store.list_conversations()]
    assert ids == [a, b]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_conversation_store.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.conversation_store'`.

- [ ] **Step 3: Write the implementation**

```python
# app/conversation_store.py
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "jarvis.db"

TITLE_MAX = 60


def _now():
    return datetime.now(timezone.utc).isoformat()


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS conversations "
        "(id TEXT PRIMARY KEY, title TEXT, created_at TEXT, updated_at TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS messages "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id TEXT, "
        "role TEXT, content TEXT, created_at TEXT)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id)"
    )
    return conn


def new_session():
    sid = str(uuid.uuid4())
    now = _now()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO conversations (id, title, created_at, updated_at) "
            "VALUES (?, ?, ?, ?)",
            (sid, "", now, now),
        )
        conn.commit()
    return sid


def append(session_id, role, content):
    now = _now()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content, created_at) "
            "VALUES (?, ?, ?, ?)",
            (session_id, role, content, now),
        )
        if role == "user":
            conn.execute(
                "UPDATE conversations SET title = ? "
                "WHERE id = ? AND (title IS NULL OR title = '')",
                (content[:TITLE_MAX], session_id),
            )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?", (now, session_id)
        )
        conn.commit()


def get(session_id):
    with _connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? "
            "ORDER BY id",
            (session_id,),
        ).fetchall()
    return [{"role": role, "content": content} for role, content in rows]


def list_conversations():
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, title, updated_at FROM conversations ORDER BY updated_at DESC"
        ).fetchall()
    return [{"id": i, "title": t, "updated_at": u} for i, t, u in rows]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_conversation_store.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Gitignore the DB and commit**

Add to `.gitignore`:
```
# App DB (conversations + memory, user data)
jarvis.db
```
```bash
git add app/conversation_store.py tests/test_conversation_store.py .gitignore
git commit -m "feat(web-ui): add SQLite conversation store"
```

---

### Task 2: Memory store (`app/memory_store.py`)

**Files:**
- Create: `app/memory_store.py`
- Test: `tests/test_memory_store.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `DB_PATH` (module attribute)
  - `remember(content: str) -> None`
  - `list_memories() -> list[str]`  (oldest-first)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_memory_store.py
import pytest

import app.memory_store as mem


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(mem, "DB_PATH", tmp_path / "jarvis.db")


def test_remember_and_list_roundtrip():
    mem.remember("Robert prefers clean code")
    mem.remember("Robert uses PyCharm")
    assert mem.list_memories() == [
        "Robert prefers clean code",
        "Robert uses PyCharm",
    ]


def test_list_empty_is_empty():
    assert mem.list_memories() == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_memory_store.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.memory_store'`.

- [ ] **Step 3: Write the implementation**

```python
# app/memory_store.py
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "jarvis.db"


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS memories "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT, created_at TEXT)"
    )
    return conn


def remember(content):
    with _connect() as conn:
        conn.execute(
            "INSERT INTO memories (content, created_at) VALUES (?, ?)",
            (content, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()


def list_memories():
    with _connect() as conn:
        rows = conn.execute("SELECT content FROM memories ORDER BY id").fetchall()
    return [row[0] for row in rows]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_memory_store.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add app/memory_store.py tests/test_memory_store.py
git commit -m "feat(web-ui): add SQLite memory store"
```

---

### Task 3: Agent tool-use loop (`app/agent.py`)

**Files:**
- Create: `app/agent.py`
- Test: `tests/test_agent.py`

**Interfaces:**
- Consumes: `app.tools.{open_app,run_macro,cancel_action}` (dict→str); `app.memory_store.remember` (Task 2); `app.llm.{get_client,extract_text,DEFAULT_SYSTEM}`.
- Produces:
  - `ActionEvent(tool: str, input: dict, result: str)` (dataclass)
  - `AgentResult(reply: str, actions: list[ActionEvent], model: str, input_tokens: int, output_tokens: int)` (dataclass)
  - `TOOLS` (list of Anthropic tool dicts), `DISPATCH` (dict name→callable)
  - `run_agent(history, user_message, *, memories=(), settings=None, client=None, max_steps=8) -> AgentResult`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_agent.py
from types import SimpleNamespace

import pytest

import app.agent as agent
import app.memory_store as mem


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(mem, "DB_PATH", tmp_path / "jarvis.db")


def _text(text, model="m", in_tok=5, out_tok=3):
    return SimpleNamespace(
        stop_reason="end_turn",
        content=[SimpleNamespace(type="text", text=text)],
        model=model,
        usage=SimpleNamespace(input_tokens=in_tok, output_tokens=out_tok),
    )


def _tool_use(name, inp, tool_id="t1"):
    return SimpleNamespace(
        stop_reason="tool_use",
        content=[SimpleNamespace(type="tool_use", name=name, input=inp, id=tool_id)],
        model="m",
        usage=SimpleNamespace(input_tokens=7, output_tokens=2),
    )


class FakeClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    @property
    def messages(self):
        return SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


def _settings():
    return SimpleNamespace(anthropic_model="m", max_tokens=256)


def test_plain_reply_no_tools():
    client = FakeClient([_text("Hello.", in_tok=10, out_tok=4)])
    result = agent.run_agent([], "hi", settings=_settings(), client=client)
    assert result.reply == "Hello."
    assert result.actions == []
    assert result.input_tokens == 10 and result.output_tokens == 4


def test_dispatches_tool_then_replies(monkeypatch):
    seen = []
    monkeypatch.setitem(agent.DISPATCH, "open_app", lambda p: seen.append(p) or "Opening Photos.")
    client = FakeClient([_tool_use("open_app", {"app": "photos"}), _text("Done.")])
    result = agent.run_agent([], "open photos", settings=_settings(), client=client)
    assert seen == [{"app": "photos"}]
    assert result.reply == "Done."
    assert result.actions[0].tool == "open_app"
    assert result.actions[0].result == "Opening Photos."
    # second call carried the tool_result back to Claude
    second = client.calls[1]["messages"]
    assert second[-1]["role"] == "user"
    assert second[-1]["content"][0]["type"] == "tool_result"


def test_unknown_tool_does_not_crash():
    client = FakeClient([_tool_use("bogus", {}), _text("Recovered.")])
    result = agent.run_agent([], "x", settings=_settings(), client=client)
    assert result.reply == "Recovered."
    assert "bogus" in result.actions[0].result.lower()


def test_remember_tool_persists_fact():
    client = FakeClient([_tool_use("remember", {"fact": "likes tea"}), _text("Noted.")])
    agent.run_agent([], "remember I like tea", settings=_settings(), client=client)
    assert mem.list_memories() == ["likes tea"]


def test_memories_injected_into_system_prompt():
    client = FakeClient([_text("ok")])
    agent.run_agent([], "hi", memories=["likes tea"], settings=_settings(), client=client)
    assert "likes tea" in client.calls[0]["system"]


def test_max_steps_caps_tool_loop():
    # Always returns tool_use -> loop must terminate by max_steps.
    client = FakeClient([_tool_use("open_app", {"app": "x"})] * 10)
    agent.DISPATCH_BACKUP = dict(agent.DISPATCH)
    result = agent.run_agent([], "loop", settings=_settings(), client=client, max_steps=3)
    assert len(client.calls) == 3
    assert result.actions  # recorded what it did before giving up
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_agent.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.agent'`.

- [ ] **Step 3: Write the implementation**

```python
# app/agent.py
from dataclasses import dataclass, field

from app import llm, memory_store, tools

TOOL_GUIDANCE = (
    "You can take real actions with tools. When the user asks to open an app, "
    "call open_app. When they ask to open a named environment/setup, call "
    "run_macro. When they ask to stop something in progress, call cancel_action. "
    "When you learn a durable fact about the user worth recalling in future "
    "conversations, call remember with a short statement of that fact."
)

TOOLS = [
    {
        "name": "open_app",
        "description": "Open an application on the user's computer by name.",
        "input_schema": {
            "type": "object",
            "properties": {"app": {"type": "string", "description": "App name."}},
            "required": ["app"],
        },
    },
    {
        "name": "run_macro",
        "description": "Run a saved macro that opens a group of apps.",
        "input_schema": {
            "type": "object",
            "properties": {"macro": {"type": "string", "description": "Macro name."}},
            "required": ["macro"],
        },
    },
    {
        "name": "cancel_action",
        "description": "Cancel the action currently in progress.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "remember",
        "description": "Store a durable fact about the user for future conversations.",
        "input_schema": {
            "type": "object",
            "properties": {"fact": {"type": "string", "description": "The fact."}},
            "required": ["fact"],
        },
    },
]


def _remember(params):
    fact = (params or {}).get("fact", "").strip()
    if fact:
        memory_store.remember(fact)
    return "Got it — I'll remember that."


DISPATCH = {
    "open_app": tools.open_app,
    "run_macro": tools.run_macro,
    "cancel_action": tools.cancel_action,
    "remember": _remember,
}


@dataclass
class ActionEvent:
    tool: str
    input: dict
    result: str


@dataclass
class AgentResult:
    reply: str
    actions: list = field(default_factory=list)
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


def _system(memories):
    system = llm.DEFAULT_SYSTEM + "\n\n" + TOOL_GUIDANCE
    if memories:
        facts = "\n".join(f"- {m}" for m in memories)
        system += "\n\nWhat you remember about the user:\n" + facts
    return system


def run_agent(history, user_message, *, memories=(), settings=None, client=None, max_steps=8):
    settings = settings or llm.get_settings()
    client = client or llm.get_client()
    system = _system(memories)
    messages = [*history, {"role": "user", "content": user_message}]
    actions = []
    in_tok = out_tok = 0
    model = settings.anthropic_model

    for _ in range(max_steps):
        resp = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=settings.max_tokens,
            system=system,
            tools=TOOLS,
            messages=messages,
        )
        in_tok += resp.usage.input_tokens
        out_tok += resp.usage.output_tokens
        model = resp.model
        if resp.stop_reason != "tool_use":
            return AgentResult(llm.extract_text(resp), actions, model, in_tok, out_tok)
        messages.append({"role": "assistant", "content": resp.content})
        results = []
        for block in resp.content:
            if getattr(block, "type", None) != "tool_use":
                continue
            try:
                result = DISPATCH[block.name](dict(block.input))
            except Exception as exc:  # unknown tool / tool error -> recoverable
                result = f"Tool {block.name} failed: {exc}"
            actions.append(ActionEvent(block.name, dict(block.input), result))
            results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": result}
            )
        messages.append({"role": "user", "content": results})

    return AgentResult(
        "I stopped after several tool steps without finishing.", actions, model, in_tok, out_tok
    )
```

Note: `run_agent` resolves the client via `llm.get_client()` **through the module**, so tests that `monkeypatch.setattr("app.llm.get_client", ...)` work. `llm.get_settings` is already available (`app/llm.py` imports `get_settings` from `app.config`), so `llm.get_settings()` resolves.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_agent.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add app/agent.py tests/test_agent.py
git commit -m "feat(web-ui): add Claude tool-use loop with remember tool"
```

---

### Task 4: Wire `/chat` to the agent + conversation/memory endpoints

**Files:**
- Modify: `app/main.py`
- Modify: `app/schemas.py`
- Modify: `tests/test_chat.py`
- Create: `tests/test_conversations_api.py`
- Delete: `app/session.py` (replaced by `conversation_store`)

**Interfaces:**
- Consumes: `conversation_store.{new_session,append,get,list_conversations}` (Task 1); `memory_store.list_memories` (Task 2); `agent.run_agent`, `AgentResult` (Task 3).
- Produces: upgraded `POST /jarvis/chat` (response gains `actions`); `GET /jarvis/conversations`; `GET /jarvis/conversations/{id}`; `GET /jarvis/memories`.

- [ ] **Step 1: Update `app/schemas.py`**

Append the new models and extend `ChatResponse`:
```python
class ActionView(BaseModel):
    tool: str
    summary: str


class ConversationSummary(BaseModel):
    id: str
    title: str
    updated_at: str


class Message(BaseModel):
    role: str
    content: str
```
Add `actions` to `ChatResponse`:
```python
class ChatResponse(BaseModel):
    reply: str
    session_id: str
    model: str
    input_tokens: int
    output_tokens: int
    actions: list[ActionView] = []
```

- [ ] **Step 2: Rewrite `app/main.py`**

```python
import anthropic
from fastapi import FastAPI, Depends, HTTPException, APIRouter

from app.config import Settings, get_settings
from app.agent import run_agent
from app import conversation_store as store
from app import memory_store
from app import schemas

app = FastAPI(title="Jarvis", version="0.1.0")
router = APIRouter(prefix="/jarvis")


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/chat", response_model=schemas.ChatResponse)
def chat_endpoint(
    req: schemas.ChatRequest,
    settings: Settings = Depends(get_settings),
) -> schemas.ChatResponse:
    session_id = req.session_id or store.new_session()
    try:
        result = run_agent(
            store.get(session_id),
            req.message,
            memories=memory_store.list_memories(),
            settings=settings,
        )
    except anthropic.APIStatusError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except anthropic.APIConnectionError as e:
        raise HTTPException(status_code=503, detail="Upstream connection failed") from e

    store.append(session_id, "user", req.message)
    store.append(session_id, "assistant", result.reply)

    return schemas.ChatResponse(
        reply=result.reply,
        session_id=session_id,
        model=result.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        actions=[schemas.ActionView(tool=a.tool, summary=a.result) for a in result.actions],
    )


@router.get("/conversations", response_model=list[schemas.ConversationSummary])
def list_conversations_endpoint() -> list[schemas.ConversationSummary]:
    return [schemas.ConversationSummary(**c) for c in store.list_conversations()]


@router.get("/conversations/{session_id}", response_model=list[schemas.Message])
def get_conversation_endpoint(session_id: str) -> list[schemas.Message]:
    messages = store.get(session_id)
    if not messages:
        raise HTTPException(status_code=404, detail="No such conversation")
    return [schemas.Message(**m) for m in messages]


@router.get("/memories", response_model=list[str])
def list_memories_endpoint() -> list[str]:
    return memory_store.list_memories()


app.include_router(router)
```

- [ ] **Step 3: Delete the obsolete in-memory store**

```bash
git rm app/session.py
```

- [ ] **Step 4: Update `tests/test_chat.py`**

Add an autouse temp-DB fixture, give fake messages a `stop_reason`, and account for the `actions` field. Replace the whole file body below the imports:

```python
# tests/test_chat.py
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import app.conversation_store as conv_store
import app.memory_store as mem_store
from app.config import Settings, get_settings
from app.main import app


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(conv_store, "DB_PATH", tmp_path / "jarvis.db")
    monkeypatch.setattr(mem_store, "DB_PATH", tmp_path / "jarvis.db")


@pytest.fixture
def settings() -> Settings:
    return Settings(anthropic_api_key="test-key", anthropic_model="claude-opus-4-7")


@pytest.fixture
def client(settings: Settings) -> TestClient:
    app.dependency_overrides[get_settings] = lambda: settings
    yield TestClient(app)
    app.dependency_overrides.clear()


def _fake_message(text: str = "Hello back.") -> SimpleNamespace:
    return SimpleNamespace(
        stop_reason="end_turn",
        content=[SimpleNamespace(type="text", text=text)],
        model="claude-opus-4-7",
        usage=SimpleNamespace(input_tokens=10, output_tokens=4),
    )


def test_healthz(client: TestClient) -> None:
    assert client.get("/jarvis/healthz").json() == {"status": "ok"}


def test_chat_returns_reply(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.llm.get_client", lambda: SimpleNamespace(
        messages=SimpleNamespace(create=lambda **k: _fake_message("Hello back."))
    ))
    response = client.post("/jarvis/chat", json={"message": "Hi Jarvis"})
    assert response.status_code == 200
    body = response.json()
    assert body["session_id"]
    assert body["reply"] == "Hello back."
    assert body["model"] == "claude-opus-4-7"
    assert body["input_tokens"] == 10 and body["output_tokens"] == 4
    assert body["actions"] == []


def test_chat_rejects_empty_message(client: TestClient) -> None:
    assert client.post("/jarvis/chat", json={"message": ""}).status_code == 422


def test_chat_remembers_history(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    seen_messages: list[list[dict]] = []

    def fake_create(**kwargs):
        seen_messages.append(kwargs["messages"])
        return _fake_message("ack")

    monkeypatch.setattr("app.llm.get_client", lambda: SimpleNamespace(
        messages=SimpleNamespace(create=fake_create)
    ))
    first = client.post("/jarvis/chat", json={"message": "remember 42"})
    sid = first.json()["session_id"]
    second = client.post("/jarvis/chat", json={"message": "what number?", "session_id": sid})

    assert second.json()["session_id"] == sid
    assert seen_messages[0] == [{"role": "user", "content": "remember 42"}]
    assert seen_messages[1] == [
        {"role": "user", "content": "remember 42"},
        {"role": "assistant", "content": "ack"},
        {"role": "user", "content": "what number?"},
    ]
```

- [ ] **Step 5: Write the conversation/memory API tests**

```python
# tests/test_conversations_api.py
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import app.conversation_store as conv_store
import app.memory_store as mem_store
from app.config import Settings, get_settings
from app.main import app


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(conv_store, "DB_PATH", tmp_path / "jarvis.db")
    monkeypatch.setattr(mem_store, "DB_PATH", tmp_path / "jarvis.db")


@pytest.fixture
def client():
    app.dependency_overrides[get_settings] = lambda: Settings(
        anthropic_api_key="test-key", anthropic_model="claude-opus-4-7"
    )
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_list_and_get_conversation(client: TestClient):
    sid = conv_store.new_session()
    conv_store.append(sid, "user", "hi there")
    conv_store.append(sid, "assistant", "hello")

    listed = client.get("/jarvis/conversations").json()
    assert listed[0]["id"] == sid
    assert listed[0]["title"] == "hi there"

    msgs = client.get(f"/jarvis/conversations/{sid}").json()
    assert msgs == [
        {"role": "user", "content": "hi there"},
        {"role": "assistant", "content": "hello"},
    ]


def test_get_unknown_conversation_404(client: TestClient):
    assert client.get("/jarvis/conversations/nope").status_code == 404


def test_memories_endpoint(client: TestClient):
    mem_store.remember("likes tea")
    assert client.get("/jarvis/memories").json() == ["likes tea"]
```

- [ ] **Step 6: Run the full suite**

Run: `.venv/bin/python -m pytest -q`
Expected: all pass (new store/agent/api tests + macro/launcher/cancel tests still green).

- [ ] **Step 7: Commit**

```bash
git add app/main.py app/schemas.py tests/test_chat.py tests/test_conversations_api.py
git commit -m "feat(web-ui): drive /chat through the agent loop; add conversation + memory endpoints"
```

---

### Task 5: Frontend page (`app/static/`) + static mount

**Files:**
- Create: `app/static/index.html`
- Create: `app/static/app.js`
- Create: `app/static/style.css`
- Modify: `app/main.py` (mount `StaticFiles` at `/`)

**Interfaces:**
- Consumes: `POST /jarvis/chat`, `GET /jarvis/conversations`, `GET /jarvis/conversations/{id}`, `GET /jarvis/memories` (Task 4).
- Produces: a served web page. Manual acceptance (no automated frontend test).

- [ ] **Step 1: Mount static files in `app/main.py`**

Add the import and mount **after** `app.include_router(router)` (so `/jarvis/*` API routes win over the catch-all static mount):
```python
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app.mount(
    "/",
    StaticFiles(directory=Path(__file__).parent / "static", html=True),
    name="static",
)
```

- [ ] **Step 2: Create `app/static/index.html`**

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Jarvis</title>
  <link rel="stylesheet" href="/style.css" />
</head>
<body>
  <aside id="sidebar">
    <button id="new-chat">+ New chat</button>
    <ul id="conversations"></ul>
    <section id="memory">
      <h3>🧠 Jarvis remembers</h3>
      <ul id="memories"></ul>
    </section>
  </aside>
  <main>
    <div id="transcript"></div>
    <form id="composer">
      <input id="message" autocomplete="off" placeholder="Type or press 🎤…" />
      <button type="button" id="mic" title="Speak">🎤</button>
      <button type="submit">Send</button>
    </form>
  </main>
  <script src="/app.js"></script>
</body>
</html>
```

- [ ] **Step 3: Create `app/static/style.css`**

```css
* { box-sizing: border-box; }
body { margin: 0; font-family: system-ui, sans-serif; display: flex; height: 100vh; }
#sidebar { width: 260px; border-right: 1px solid #ddd; padding: 12px; overflow-y: auto; }
#sidebar button { width: 100%; padding: 8px; margin-bottom: 8px; cursor: pointer; }
#conversations, #memories { list-style: none; padding: 0; margin: 0; }
#conversations li { padding: 6px; border-radius: 6px; cursor: pointer; font-size: 14px; }
#conversations li:hover, #conversations li.active { background: #eef; }
#memory { margin-top: 16px; font-size: 13px; color: #555; }
main { flex: 1; display: flex; flex-direction: column; }
#transcript { flex: 1; overflow-y: auto; padding: 16px; }
.msg { margin: 8px 0; padding: 8px 12px; border-radius: 10px; max-width: 70%; white-space: pre-wrap; }
.msg.user { background: #d6e4ff; margin-left: auto; }
.msg.assistant { background: #f0f0f0; }
.chips { margin: 4px 0 12px; }
.chip { display: inline-block; background: #e8f5e9; border: 1px solid #c8e6c9; border-radius: 12px; padding: 2px 8px; font-size: 12px; margin-right: 4px; }
#composer { display: flex; gap: 8px; padding: 12px; border-top: 1px solid #ddd; }
#message { flex: 1; padding: 10px; }
#mic.listening { background: #ffcdd2; }
```

- [ ] **Step 4: Create `app/static/app.js`**

```javascript
let sessionId = null;

const transcript = document.getElementById("transcript");
const form = document.getElementById("composer");
const input = document.getElementById("message");
const micBtn = document.getElementById("mic");

function addMessage(role, content) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = content;
  transcript.appendChild(div);
  transcript.scrollTop = transcript.scrollHeight;
}

function addChips(actions) {
  if (!actions || !actions.length) return;
  const wrap = document.createElement("div");
  wrap.className = "chips";
  for (const a of actions) {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = `${a.tool}: ${a.summary}`;
    wrap.appendChild(chip);
  }
  transcript.appendChild(wrap);
}

function speak(text) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.speak(new SpeechSynthesisUtterance(text));
}

async function send(message) {
  addMessage("user", message);
  const res = await fetch("/jarvis/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  const data = await res.json();
  sessionId = data.session_id;
  addChips(data.actions);
  addMessage("assistant", data.reply);
  speak(data.reply);
  refreshSidebar();
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  send(message);
});

document.getElementById("new-chat").addEventListener("click", () => {
  sessionId = null;
  transcript.innerHTML = "";
});

async function refreshSidebar() {
  const convs = await (await fetch("/jarvis/conversations")).json();
  const ul = document.getElementById("conversations");
  ul.innerHTML = "";
  for (const c of convs) {
    const li = document.createElement("li");
    li.textContent = c.title || "(untitled)";
    if (c.id === sessionId) li.classList.add("active");
    li.addEventListener("click", () => openConversation(c.id));
    ul.appendChild(li);
  }
  const mems = await (await fetch("/jarvis/memories")).json();
  const mu = document.getElementById("memories");
  mu.innerHTML = "";
  for (const m of mems) {
    const li = document.createElement("li");
    li.textContent = m;
    mu.appendChild(li);
  }
}

async function openConversation(id) {
  sessionId = id;
  transcript.innerHTML = "";
  const msgs = await (await fetch(`/jarvis/conversations/${id}`)).json();
  for (const m of msgs) addMessage(m.role, m.content);
  refreshSidebar();
}

// --- Web Speech (input) ---
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SR) {
  const recog = new SR();
  recog.lang = "en-US";
  micBtn.addEventListener("click", () => {
    micBtn.classList.add("listening");
    recog.start();
  });
  recog.onresult = (e) => {
    input.value = e.results[0][0].transcript;
    micBtn.classList.remove("listening");
    form.requestSubmit();
  };
  recog.onend = () => micBtn.classList.remove("listening");
} else {
  micBtn.style.display = "none";
}

refreshSidebar();
```

- [ ] **Step 5: Run the full suite (no regressions from the mount)**

Run: `.venv/bin/python -m pytest -q`
Expected: all pass (the static mount must not shadow `/jarvis/*` — it's mounted after the router).

- [ ] **Step 6: Manual acceptance**

Run: `.venv/bin/uvicorn app.main:app --reload` then open `http://127.0.0.1:8000/`.
- Type "Hi" → reply renders and is spoken.
- "open my work environment" → action chips appear and apps open.
- Click 🎤 (Chrome), speak → it transcribes and sends.
- "remember that I like tea" → a memory appears in the sidebar; restart the server → the conversation list and memory survive.

- [ ] **Step 7: Commit**

```bash
git add app/main.py app/static/
git commit -m "feat(web-ui): vanilla chat UI with Web Speech voice and conversation/memory panels"
```

---

## Self-Review

**Spec coverage:**
- Single-user/local, `jarvis.db` gitignored, store pattern → Global Constraints + Tasks 1–2. ✓
- Web Speech voice, vanilla page served by FastAPI → Task 5. ✓
- `/chat` tool-use loop executing `open_app`/`run_macro`/`cancel_action` server-side, reusing `tools.py` → Task 3 + Task 4. ✓
- `remember` tool + memory injected into system prompt → Task 3 (`_remember`, `_system`). ✓
- Persistent conversations replacing in-memory store; persist user turn + final reply only → Tasks 1, 4. ✓
- Conversation list + reopen + memory endpoints → Task 4. ✓
- `ActionView`/`ConversationSummary`/`Message`/`ChatResponse.actions` → Task 4 Step 1. ✓
- Edge cases (unknown tool, max_steps, 404) → Task 3 + Task 4 tests. ✓
- Trust boundary (localhost, fixed allowlist) → Global Constraints. ✓

**Placeholder scan:** None — every code step shows full content. Task 5 acceptance is manual by nature (browser/mic/voice), with concrete steps.

**Type consistency:** `run_agent(history, user_message, *, memories, settings, client, max_steps) -> AgentResult`; `AgentResult(reply, actions, model, input_tokens, output_tokens)`; `ActionEvent(tool, input, result)` → mapped to `ActionView(tool, summary=result)` in `main.py`; store functions `new_session/append(sid,role,content)/get/list_conversations`; `memory_store.remember/list_memories`; `DISPATCH` keys match `TOOLS` names and the `/jarvis/*` routes match the frontend fetch paths. ✓

**Verified preconditions:** `llm.get_settings`, `llm.get_client`, and `llm.extract_text` all exist in `app/llm.py`; `tools.{open_app,run_macro,cancel_action}` exist and take a dict / return a string. No conditionals left in the plan.
