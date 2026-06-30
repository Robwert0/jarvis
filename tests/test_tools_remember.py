import pytest

import app.memory_store as mem
import app.tools as tools


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(mem, "DB_PATH", tmp_path / "jarvis.db")


def test_remember_persists_fact():
    result = tools.remember({"fact": "Robert prefers dark mode"})
    assert mem.list_memories() == ["Robert prefers dark mode"]
    assert "remember" in result.lower()


def test_remember_ignores_empty_fact():
    tools.remember({"fact": "   "})
    tools.remember({})
    assert mem.list_memories() == []


def test_remember_registered_as_client_tool():
    assert "remember" in tools.build_client_tools().tools
