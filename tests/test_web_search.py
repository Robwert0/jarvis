import pytest

import app.web_search as web_search


class FakeClient:
    def __init__(self, response=None, raises=False):
        self._response = response or {}
        self._raises = raises
        self.calls = []

    def search(self, query, **kwargs):
        self.calls.append((query, kwargs))
        if self._raises:
            raise RuntimeError("boom")
        return self._response


def test_empty_query_prompts():
    assert web_search.search("   ") == "What should I search for?"


def test_missing_client_reports_not_configured(monkeypatch):
    monkeypatch.setattr(web_search, "_default_client", lambda: None)
    assert web_search.search("weather") == "Web search isn't configured yet."


def test_formats_answer_and_sources():
    client = FakeClient({
        "answer": "It is sunny.",
        "results": [
            {"title": "Weather", "url": "http://a", "content": "..."},
            {"title": "Forecast", "url": "http://b", "content": "..."},
        ],
    })
    out = web_search.search("weather today", client=client)
    assert "It is sunny." in out
    assert "Weather (http://a)" in out
    assert "Forecast (http://b)" in out
    # passes the LLM-friendly params through
    assert client.calls[0][1]["include_answer"] is True
    assert client.calls[0][1]["max_results"] == 3


def test_falls_back_to_top_result_when_no_answer():
    client = FakeClient({
        "results": [{"title": "T", "url": "http://a", "content": "the snippet"}],
    })
    out = web_search.search("q", client=client)
    assert "the snippet" in out
    assert "T (http://a)" in out


def test_client_error_is_friendly():
    client = FakeClient(raises=True)
    assert web_search.search("q", client=client) == "I couldn't complete the search right now."
