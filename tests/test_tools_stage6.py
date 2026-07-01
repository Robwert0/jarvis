import app.tools as tools
import app.web_search as web_search
import app.system_control as system_control


def test_search_web_passes_query_and_returns_result(monkeypatch):
    seen = {}
    monkeypatch.setattr(web_search, "search", lambda q: (seen.setdefault("q", q), "RESULT")[1])
    assert tools.search_web({"query": "  cats  "}) == "RESULT"
    assert seen["q"] == "cats"


def test_search_web_handles_missing_query(monkeypatch):
    monkeypatch.setattr(web_search, "search", lambda q: f"got:{q!r}")
    assert tools.search_web({}) == "got:''"


def test_control_system_passes_action(monkeypatch):
    seen = {}
    monkeypatch.setattr(system_control, "control", lambda a: (seen.setdefault("a", a), "OK")[1])
    assert tools.control_system({"action": " lock "}) == "OK"
    assert seen["a"] == "lock"


def test_both_registered_as_client_tools():
    registered = tools.build_client_tools().tools
    assert "search_web" in registered
    assert "control_system" in registered
