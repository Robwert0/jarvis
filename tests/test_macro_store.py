import pytest

import app.macro_store as store


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "macros.db")


def test_upsert_and_get_roundtrip():
    store.upsert_macro("work", ["Visual Studio Code", "Slack"])
    assert store.get_macro("work") == ["Visual Studio Code", "Slack"]


def test_get_unknown_returns_none():
    assert store.get_macro("nope") is None


def test_list_macros_returns_all():
    store.upsert_macro("work", ["Code"])
    store.upsert_macro("game", ["Steam"])
    assert store.list_macros() == {"work": ["Code"], "game": ["Steam"]}


def test_upsert_overwrites_existing_name():
    store.upsert_macro("work", ["Code"])
    store.upsert_macro("work", ["Code", "Slack"])
    assert store.get_macro("work") == ["Code", "Slack"]
