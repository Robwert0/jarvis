import app.agent as agent


def test_new_tools_declared():
    names = {t["name"] for t in agent.TOOLS}
    assert "search_web" in names
    assert "control_system" in names


def test_search_web_schema_requires_query():
    tool = next(t for t in agent.TOOLS if t["name"] == "search_web")
    assert tool["input_schema"]["required"] == ["query"]


def test_control_system_schema_requires_action():
    tool = next(t for t in agent.TOOLS if t["name"] == "control_system")
    assert tool["input_schema"]["required"] == ["action"]


def test_dispatch_maps_new_tools():
    import app.tools as tools
    assert agent.DISPATCH["search_web"] is tools.search_web
    assert agent.DISPATCH["control_system"] is tools.control_system
