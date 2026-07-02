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


def test_delete_conversation(client: TestClient):
    sid = conv_store.new_session()
    conv_store.append(sid, "user", "hi")
    assert client.delete(f"/jarvis/conversations/{sid}").status_code == 204
    assert client.get(f"/jarvis/conversations/{sid}").status_code == 404


def test_delete_conversation_unknown_404(client: TestClient):
    assert client.delete("/jarvis/conversations/nope").status_code == 404


def test_create_conversation_201(client):
    r = client.post("/jarvis/conversations")
    assert r.status_code == 201
    assert r.json()["session_id"]


def test_append_message_and_read_back(client):
    sid = client.post("/jarvis/conversations").json()["session_id"]
    r = client.post(
        f"/jarvis/conversations/{sid}/messages",
        json={"role": "user", "content": "hello from voice"},
    )
    assert r.status_code == 204
    client.post(
        f"/jarvis/conversations/{sid}/messages",
        json={"role": "assistant", "content": "hi Robert"},
    )
    assert client.get(f"/jarvis/conversations/{sid}").json() == [
        {"role": "user", "content": "hello from voice"},
        {"role": "assistant", "content": "hi Robert"},
    ]
    convs = client.get("/jarvis/conversations").json()
    assert convs[0]["id"] == sid
    assert convs[0]["title"] == "hello from voice"


def test_append_message_unknown_conversation_404(client):
    r = client.post(
        "/jarvis/conversations/nope/messages",
        json={"role": "user", "content": "hi"},
    )
    assert r.status_code == 404


def test_append_message_invalid_role_422(client):
    sid = client.post("/jarvis/conversations").json()["session_id"]
    r = client.post(
        f"/jarvis/conversations/{sid}/messages",
        json={"role": "tool", "content": "hi"},
    )
    assert r.status_code == 422
