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
    def fake_create(**kwargs):
        assert kwargs["model"] == "claude-opus-4-7"
        return _fake_message("Hello back.")

    monkeypatch.setattr("app.llm.get_client", lambda: SimpleNamespace(
        messages=SimpleNamespace(create=fake_create)
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
