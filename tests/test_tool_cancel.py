import threading
import time

import pytest

import app.cancellation as c
import app.tools as tools


@pytest.fixture(autouse=True)
def reset_current():
    c._current = None
    yield
    c._current = None


def test_cancel_action_nothing_running():
    assert tools.cancel_action({}) == "There's nothing running to cancel."


def test_cancel_action_reports_partial_progress():
    token = c.begin()

    def worker():
        while not token.cancelled:
            time.sleep(0.1)
        token.set_progress("Completed 3 of 16 steps")
        token.mark_stopped()
        c.end(token)

    t = threading.Thread(target=worker)
    t.start()
    try:
        result = tools.cancel_action({})
    finally:
        t.join(timeout=2)

    assert result == "Stopped. Completed 3 of 16 steps"


def test_cancel_action_times_out_when_action_ignores_flag(monkeypatch):
    monkeypatch.setattr(tools, "CANCEL_WAIT_TIMEOUT", 0.1)
    token = c.begin()
    try:
        result = tools.cancel_action({})
    finally:
        token.mark_stopped()
        c.end(token)
    assert result == "Cancellation requested, but it hasn't stopped yet."


def test_cancel_action_registered():
    registered = tools.build_client_tools()
    assert "cancel_action" in registered.tools