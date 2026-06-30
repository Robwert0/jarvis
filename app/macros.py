import difflib
import time

from app import macro_store
from app.cancellation import begin, end
from app.launcher import get_launcher

RECENCY_WINDOW = 120.0
_recently_launched = {}    # app name -> monotonic launch time


def _join(names):
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def _summary(opened, skipped, not_found):
    parts = []
    if opened:
        parts.append("opened " + _join(opened))
    if skipped:
        parts.append(_join(skipped) + " already running")
    if not_found:
        parts.append("couldn't find " + _join(not_found))
    return "; ".join(parts) if parts else "nothing to do"


def _match(name, macros):
    key = name.strip().lower()
    hits = [m for m in macros if key in m.lower()]
    if hits:
        return min(hits, key=len)
    by_lower = {m.lower(): m for m in macros}
    close = difflib.get_close_matches(key, list(by_lower), n=1, cutoff=0.6)
    return by_lower[close[0]] if close else None


def _recently(app, now):
    ts = _recently_launched.get(app)
    return ts is not None and (now() - ts) < RECENCY_WINDOW


def _entry(item):
    """Normalize a macro entry into (app_name, args). Entries are either a bare
    string ("Slack") or a dict {"app": ..., "args": [...]}."""
    if isinstance(item, dict):
        return item.get("app", ""), item.get("args") or []
    return item, []


def run(name, *, store=macro_store, launcher=None, now=time.monotonic):
    if launcher is None:
        launcher = get_launcher()
    all_macros = store.list_macros()
    matched = _match(name, all_macros)
    if matched is None:
        names = ", ".join(all_macros) if all_macros else "none"
        return f"I don't have a macro called {name}. You have: {names}."
    apps = all_macros[matched]
    if not apps:
        return f"The {matched} macro has no apps in it."

    token = begin()
    opened, skipped, not_found = [], [], []
    try:
        for item in apps:
            if token.cancelled:
                break
            app, args = _entry(item)
            if launcher.is_running(app) or _recently(app, now):
                skipped.append(app)
            else:
                result = launcher.launch(app, args)
                if result.ok:
                    opened.append(app)
                    _recently_launched[app] = now()
                else:
                    not_found.append(app)
            token.set_progress(_summary(opened, skipped, not_found))
        body = _summary(opened, skipped, not_found)
        if token.cancelled:
            return f"Stopped — {body} before you stopped me."
        return body[:1].upper() + body[1:] + "."
    finally:
        token.mark_stopped()
        end(token)
