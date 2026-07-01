from tavily import TavilyClient

from app.config import get_settings

MAX_RESULTS = 3


def _default_client():
    key = get_settings().tavily_api_key
    if not key:
        return None
    return TavilyClient(api_key=key)


def search(query, *, client=None):
    query = (query or "").strip()
    if not query:
        return "What should I search for?"
    if client is None:
        client = _default_client()
    if client is None:
        return "Web search isn't configured yet."
    try:
        response = client.search(query, include_answer=True, max_results=MAX_RESULTS)
    except Exception:
        return "I couldn't complete the search right now."
    return _format(response)


def _format(response):
    results = response.get("results", [])
    answer = (response.get("answer") or "").strip()
    lines = []
    if answer:
        lines.append(answer)
    elif results:
        lines.append((results[0].get("content") or "").strip())
    sources = [
        f"- {r.get('title', 'Untitled')} ({r.get('url', '')})"
        for r in results[:MAX_RESULTS]
    ]
    if sources:
        lines.append("Sources:")
        lines.extend(sources)
    text = "\n".join(line for line in lines if line).strip()
    return text or "I didn't find anything useful."
