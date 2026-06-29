import threading
import time

import pytest

import app.cancellation as c


@pytest.fixture(autouse=True)
def reset_current():
    c._current = None
    yield
    c._current = None


def test_token_cancel_and_progress():
    tok = c.CancelToken()
    assert tok.cancelled == False

    tok.cancel()
    assert tok.cancelled == True

    tok.set_progress("Completed 2 of 16 steps")
    assert tok.progress == "Completed 2 of 16 steps"


def test_begin_current_end_roundtrip():
    tok = c.begin()
    assert c.current() is tok
    c.end(tok)
    assert c.current() is None


def test_wait_stopped_timeout_then_signal():
    tok = c.CancelToken()
    assert tok.wait_stopped(timeout=0.01) is False
    tok.mark_stopped()
    assert tok.wait_stopped(timeout=0.01) is True


def test_end_with_stale_token_does_not_clear_newer():
    t1 = c.begin()
    t2 = c.begin()
    c.end(t1)
    assert c.current() is t2


def test_begin_warns_when_previous_still_active(capsys):
    c.begin()
    c.begin()
    assert "WARNING" in capsys.readouterr().out