from types import SimpleNamespace

import pytest

import app.memory_store as mem
import app.voice as voice


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(mem, "DB_PATH", tmp_path / "jarvis.db")


class FakeConversation:
    def __init__(self):
        self.started = False
        self.contextual_updates = []
        self.ended = False

    def start_session(self):
        self.started = True

    def send_contextual_update(self, text):
        self.contextual_updates.append(text)

    def wait_for_session_end(self):
        return "conv-123"

    def end_session(self):
        self.ended = True


def test_memory_block_empty():
    assert voice.memory_block([]) == ""


def test_memory_block_lists_facts():
    block = voice.memory_block(["likes tea", "uses PyCharm"])
    assert "likes tea" in block and "uses PyCharm" in block


def test_run_session_bridges_memory():
    mem.remember("likes tea")
    fake = FakeConversation()
    cid = voice.run_session(settings=SimpleNamespace(), conversation_factory=lambda s: fake)
    assert fake.started is True
    assert len(fake.contextual_updates) == 1
    assert "likes tea" in fake.contextual_updates[0]
    assert cid == "conv-123"


def test_run_session_skips_update_when_no_memory():
    fake = FakeConversation()
    voice.run_session(settings=SimpleNamespace(), conversation_factory=lambda s: fake)
    assert fake.contextual_updates == []
