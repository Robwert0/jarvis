import app.tools as tools


def test_run_macro_delegates_to_macros_run(monkeypatch):
    calls = []
    monkeypatch.setattr(tools.macros, "run", lambda name: calls.append(name) or "ok")
    assert tools.run_macro({"macro": "work"}) == "ok"
    assert calls == ["work"]


def test_run_macro_strips_and_handles_missing_param(monkeypatch):
    calls = []
    monkeypatch.setattr(tools.macros, "run", lambda name: calls.append(name) or "ok")
    tools.run_macro({"macro": "  work  "})
    tools.run_macro({})
    assert calls == ["work", ""]


def test_run_macro_registered():
    assert "run_macro" in tools.build_client_tools().tools
