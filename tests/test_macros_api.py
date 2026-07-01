import pytest
from fastapi.testclient import TestClient

import app.macro_store as macro_store
from app.main import app


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(macro_store, "DB_PATH", tmp_path / "macros.db")


@pytest.fixture
def client():
    return TestClient(app)


def test_create_then_get_and_list(client):
    r = client.post("/jarvis/macros", json={"name": "work", "apps": ["chrome"]})
    assert r.status_code == 201
    assert r.json() == {"name": "work", "apps": ["chrome"]}

    assert client.get("/jarvis/macros/work").json() == {"name": "work", "apps": ["chrome"]}
    assert client.get("/jarvis/macros").json() == [{"name": "work", "apps": ["chrome"]}]


def test_create_duplicate_conflicts(client):
    client.post("/jarvis/macros", json={"name": "work", "apps": ["chrome"]})
    r = client.post("/jarvis/macros", json={"name": "work", "apps": ["firefox"]})
    assert r.status_code == 409


def test_get_unknown_404(client):
    assert client.get("/jarvis/macros/nope").status_code == 404


def test_update_upserts(client):
    client.post("/jarvis/macros", json={"name": "work", "apps": ["chrome"]})
    r = client.put("/jarvis/macros/work", json={"apps": [{"app": "code", "args": ["--x"]}]})
    assert r.status_code == 200
    assert r.json()["apps"] == [{"app": "code", "args": ["--x"]}]


def test_update_creates_when_absent(client):
    r = client.put("/jarvis/macros/fresh", json={"apps": ["chrome"]})
    assert r.status_code == 200
    assert client.get("/jarvis/macros/fresh").status_code == 200


def test_delete(client):
    client.post("/jarvis/macros", json={"name": "work", "apps": ["chrome"]})
    assert client.delete("/jarvis/macros/work").status_code == 204
    assert client.get("/jarvis/macros/work").status_code == 404


def test_delete_unknown_404(client):
    assert client.delete("/jarvis/macros/nope").status_code == 404


def test_invalid_body_422(client):
    assert client.post("/jarvis/macros", json={"name": "x", "apps": [123]}).status_code == 422
    assert client.post("/jarvis/macros", json={"name": "x", "apps": [{"args": ["--x"]}]}).status_code == 422
