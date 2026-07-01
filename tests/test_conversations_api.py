# tests/test_conversations_api.py
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


def test_memories_endpoint_returns_detailed_shape(client: TestClient):
    mem_store.remember("likes tea")
    rows = client.get("/jarvis/memories").json()
    assert rows[0]["content"] == "likes tea"
    assert isinstance(rows[0]["id"], int)


def test_delete_memory(client: TestClient):
    mem_store.remember("likes tea")
    mem_id = client.get("/jarvis/memories").json()[0]["id"]
    assert client.delete(f"/jarvis/memories/{mem_id}").status_code == 204
    assert client.get("/jarvis/memories").json() == []


def test_delete_memory_unknown_404(client: TestClient):
    assert client.delete("/jarvis/memories/999").status_code == 404
