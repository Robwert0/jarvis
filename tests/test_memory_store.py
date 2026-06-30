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
