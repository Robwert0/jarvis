from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app


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
        content=[SimpleNamespace(type="text", text=text)],
        model="claude-opus-4-7",
        usage=SimpleNamespace(input_tokens=10, output_tokens=4),
    )


def test_healthz(client: TestClient) -> None:
    assert client.get("/healthz").json() == {"status": "ok"}


def test_chat_returns_reply(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_create(**kwargs):
        assert kwargs["model"] == "claude-opus-4-7"
        assert kwargs["messages"] == [{"role": "user", "content": "Hi Jarvis"}]
        return _fake_message("Hello back.")

    monkeypatch.setattr("app.llm.get_client", lambda: SimpleNamespace(
        messages=SimpleNamespace(create=fake_create)
    ))

    response = client.post("/chat", json={"message": "Hi Jarvis"})

    assert response.status_code == 200
    assert response.json() == {
        "reply": "Hello back.",
        "model": "claude-opus-4-7",
        "input_tokens": 10,
        "output_tokens": 4,
    }


def test_chat_rejects_empty_message(client: TestClient) -> None:
    response = client.post("/chat", json={"message": ""})
    assert response.status_code == 422
