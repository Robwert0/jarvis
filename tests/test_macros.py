import pytest

import app.cancellation as c
import app.macros as macros
from app.launcher import LaunchResult


@pytest.fixture(autouse=True)
def reset_state():
    c._current = None
    macros._recently_launched.clear()
    yield
    c._current = None
    macros._recently_launched.clear()


class FakeStore:
    def __init__(self, data):
        self._data = data

    def list_macros(self):
        return dict(self._data)

    def get_macro(self, name):
        return self._data.get(name)


class FakeLauncher:
    def __init__(self, running=(), fail=(), cancel_after=None):
        self.running = set(running)
        self.fail = set(fail)
        self.cancel_after = cancel_after
        self.launched = []

    def is_running(self, app):
        return app in self.running

    def launch(self, app):
        self.launched.append(app)
        if self.cancel_after and len(self.launched) >= self.cancel_after:
            c.current().cancel()
        ok = app not in self.fail
        return LaunchResult(ok, f"Opening {app}." if ok else f"couldn't find {app}")


def run(name, store, launcher, now=lambda: 1000.0):
    return macros.run(name, store=store, launcher=launcher, now=now)


def test_happy_path_launches_all():
    fl = FakeLauncher()
    summary = run("work", FakeStore({"work": ["Code", "Slack", "Chrome"]}), fl)
    assert fl.launched == ["Code", "Slack", "Chrome"]
    assert "opened" in summary.lower()
    assert "Code" in summary and "Slack" in summary and "Chrome" in summary


def test_skips_already_running():
    fl = FakeLauncher(running=["Slack"])
    summary = run("work", FakeStore({"work": ["Code", "Slack"]}), fl)
    assert fl.launched == ["Code"]            # Slack skipped
    assert "already running" in summary.lower()
    assert "Slack" in summary


def test_not_found_app_does_not_abort_rest():
    fl = FakeLauncher(fail=["Spotofy"])
    summary = run("work", FakeStore({"work": ["Spotofy", "Code"]}), fl)
    assert fl.launched == ["Spotofy", "Code"]  # attempted both
    assert "couldn't find" in summary.lower()
    assert "Code" in summary


def test_unknown_macro_lists_available():
    summary = run("zzz", FakeStore({"work": ["Code"], "game": ["Steam"]}), FakeLauncher())
    assert "work" in summary and "game" in summary


def test_empty_macro():
    summary = run("work", FakeStore({"work": []}), FakeLauncher())
    assert "no apps" in summary.lower()


def test_cancel_mid_macro_stops_and_reports_progress():
    fl = FakeLauncher(cancel_after=2)
    summary = run("work", FakeStore({"work": ["Code", "Slack", "Chrome"]}), fl)
    assert fl.launched == ["Code", "Slack"]    # Chrome never launched
    assert "stopped" in summary.lower()
    # token.progress carries the speakable cumulative summary for cancel_action
    # (token is cleared by end(); assert via the returned summary instead)
    assert "Code" in summary and "Slack" in summary


def test_recency_window_skips_recently_launched():
    macros._recently_launched["Code"] = 1000.0           # "launched now"
    fl = FakeLauncher()
    summary = run("work", FakeStore({"work": ["Code"]}), fl, now=lambda: 1050.0)  # 50s later
    assert fl.launched == []                              # within 120s window -> skipped
    assert "already running" in summary.lower() or "Code" in summary


def test_recency_window_expired_relaunches():
    macros._recently_launched["Code"] = 1000.0
    fl = FakeLauncher()
    run("work", FakeStore({"work": ["Code"]}), fl, now=lambda: 1200.0)  # 200s later (> 120)
    assert fl.launched == ["Code"]
