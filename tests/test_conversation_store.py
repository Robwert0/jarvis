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


import app.conversation_store as conv_store


def test_delete_conversation_removes_row_and_messages(tmp_path, monkeypatch):
    monkeypatch.setattr(conv_store, "DB_PATH", tmp_path / "jarvis.db")
    sid = conv_store.new_session()
    conv_store.append(sid, "user", "hi")
    assert conv_store.delete_conversation(sid) is True
    assert conv_store.get(sid) == []
    assert all(c["id"] != sid for c in conv_store.list_conversations())


def test_delete_conversation_unknown_returns_false(tmp_path, monkeypatch):
    monkeypatch.setattr(conv_store, "DB_PATH", tmp_path / "jarvis.db")
    assert conv_store.delete_conversation("nope") is False
