import httpx
import pytest
from fastapi.testclient import TestClient

import app.voice_api as voice_api
from app.agent import DISPATCH
from app.config import Settings, get_settings
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def configure(elevenlabs_api_key=None, elevenlabs_agent_id=None):
    app.dependency_overrides[get_settings] = lambda: Settings(
        anthropic_api_key="test-key",
        elevenlabs_api_key=elevenlabs_api_key,
        elevenlabs_agent_id=elevenlabs_agent_id,
    )


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


class FakeResponse:
    def __init__(self, payload=None, error=False):
        self._payload = payload or {}
        self._error = error

    def raise_for_status(self):
        if self._error:
            raise httpx.HTTPStatusError("boom", request=None, response=None)

    def json(self):
        return self._payload


def test_signed_url_unconfigured_503(client):
    configure()
    r = client.get("/jarvis/voice/signed-url")
    assert r.status_code == 503


def test_signed_url_ok(client, monkeypatch):
    configure(elevenlabs_api_key="k", elevenlabs_agent_id="a")
    calls = {}

    def fake_get(url, *, params, headers, timeout):
        calls.update(url=url, params=params, headers=headers)
        return FakeResponse({"signed_url": "wss://signed"})

    monkeypatch.setattr(voice_api, "_http_get", fake_get)
    r = client.get("/jarvis/voice/signed-url")
    assert r.status_code == 200
    assert r.json() == {"signed_url": "wss://signed"}
    assert calls["params"] == {"agent_id": "a"}
    assert calls["headers"] == {"xi-api-key": "k"}


def test_signed_url_upstream_error_502(client, monkeypatch):
    configure(elevenlabs_api_key="k", elevenlabs_agent_id="a")
    monkeypatch.setattr(voice_api, "_http_get", lambda *a, **kw: FakeResponse(error=True))
    r = client.get("/jarvis/voice/signed-url")
    assert r.status_code == 502


def test_signed_url_network_error_502(client, monkeypatch):
    def fake_get(*a, **kw):
        raise httpx.ConnectError("no network")

    monkeypatch.setattr(voice_api, "_http_get", fake_get)
    configure(elevenlabs_api_key="k", elevenlabs_agent_id="a")
    r = client.get("/jarvis/voice/signed-url")
    assert r.status_code == 502


def test_execute_tool_dispatches(client, monkeypatch):
    monkeypatch.setitem(DISPATCH, "open_app", lambda params: f"opened {params['app']}")
    r = client.post("/jarvis/tools/open_app", json={"app": "chrome"})
    assert r.status_code == 200
    assert r.json() == {"result": "opened chrome"}


def test_execute_tool_empty_body(client, monkeypatch):
    monkeypatch.setitem(DISPATCH, "cancel_action", lambda params: f"params={params}")
    r = client.post("/jarvis/tools/cancel_action")
    assert r.status_code == 200
    assert r.json() == {"result": "params={}"}


def test_execute_tool_unknown_404(client):
    r = client.post("/jarvis/tools/nope", json={})
    assert r.status_code == 404


def test_wake_config_unconfigured_503(client):
    configure()
    r = client.get("/jarvis/voice/wake-config")
    assert r.status_code == 503


def test_wake_config_ok(client):
    app.dependency_overrides[get_settings] = lambda: Settings(
        anthropic_api_key="test-key", picovoice_access_key="pv-key"
    )
    r = client.get("/jarvis/voice/wake-config")
    assert r.status_code == 200
    assert r.json() == {"access_key": "pv-key"}
