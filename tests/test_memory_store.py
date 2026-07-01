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


def test_list_memories_detailed_shape():
    mem.remember("likes tea")
    rows = mem.list_memories_detailed()
    assert len(rows) == 1
    assert rows[0]["content"] == "likes tea"
    assert isinstance(rows[0]["id"], int)
    assert rows[0]["created_at"]


def test_delete_memory():
    mem.remember("likes tea")
    mem_id = mem.list_memories_detailed()[0]["id"]
    assert mem.delete_memory(mem_id) is True
    assert mem.list_memories() == []


def test_delete_memory_unknown_returns_false():
    assert mem.delete_memory(999) is False
