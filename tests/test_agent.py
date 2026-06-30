from types import SimpleNamespace

import pytest

import app.agent as agent
import app.memory_store as mem


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(mem, "DB_PATH", tmp_path / "jarvis.db")


def _text(text, model="m", in_tok=5, out_tok=3):
    return SimpleNamespace(
        stop_reason="end_turn",
        content=[SimpleNamespace(type="text", text=text)],
        model=model,
        usage=SimpleNamespace(input_tokens=in_tok, output_tokens=out_tok),
    )


def _tool_use(name, inp, tool_id="t1"):
    return SimpleNamespace(
        stop_reason="tool_use",
        content=[SimpleNamespace(type="tool_use", name=name, input=inp, id=tool_id)],
        model="m",
        usage=SimpleNamespace(input_tokens=7, output_tokens=2),
    )


class FakeClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    @property
    def messages(self):
        return SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


def _settings():
    return SimpleNamespace(anthropic_model="m", max_tokens=256)


def test_plain_reply_no_tools():
    client = FakeClient([_text("Hello.", in_tok=10, out_tok=4)])
    result = agent.run_agent([], "hi", settings=_settings(), client=client)
    assert result.reply == "Hello."
    assert result.actions == []
    assert result.input_tokens == 10 and result.output_tokens == 4


def test_dispatches_tool_then_replies(monkeypatch):
    seen = []
    monkeypatch.setitem(agent.DISPATCH, "open_app", lambda p: seen.append(p) or "Opening Photos.")
    client = FakeClient([_tool_use("open_app", {"app": "photos"}), _text("Done.")])
    result = agent.run_agent([], "open photos", settings=_settings(), client=client)
    assert seen == [{"app": "photos"}]
    assert result.reply == "Done."
    assert result.actions[0].tool == "open_app"
    assert result.actions[0].result == "Opening Photos."
    # second call carried the tool_result back to Claude
    second = client.calls[1]["messages"]
    assert second[-1]["role"] == "user"
    assert second[-1]["content"][0]["type"] == "tool_result"


def test_unknown_tool_does_not_crash():
    client = FakeClient([_tool_use("bogus", {}), _text("Recovered.")])
    result = agent.run_agent([], "x", settings=_settings(), client=client)
    assert result.reply == "Recovered."
    assert "bogus" in result.actions[0].result.lower()


def test_remember_tool_persists_fact():
    client = FakeClient([_tool_use("remember", {"fact": "likes tea"}), _text("Noted.")])
    agent.run_agent([], "remember I like tea", settings=_settings(), client=client)
    assert mem.list_memories() == ["likes tea"]


def test_memories_injected_into_system_prompt():
    client = FakeClient([_text("ok")])
    agent.run_agent([], "hi", memories=["likes tea"], settings=_settings(), client=client)
    assert "likes tea" in client.calls[0]["system"]


def test_max_steps_caps_tool_loop():
    # Always returns tool_use -> loop must terminate by max_steps.
    client = FakeClient([_tool_use("open_app", {"app": "x"})] * 10)
    result = agent.run_agent([], "loop", settings=_settings(), client=client, max_steps=3)
    assert len(client.calls) == 3
    assert result.actions  # recorded what it did before giving up
