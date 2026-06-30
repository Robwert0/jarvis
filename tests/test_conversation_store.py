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
