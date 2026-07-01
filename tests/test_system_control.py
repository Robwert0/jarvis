import pytest

import app.system_control as sc


class FakeRun:
    def __init__(self, raises=False):
        self.commands = []
        self._raises = raises

    def __call__(self, command):
        self.commands.append(command)
        if self._raises:
            raise RuntimeError("no interop")


def test_lock_runs_rundll32():
    run = FakeRun()
    out = sc.control("lock", run=run)
    assert run.commands == [["rundll32.exe", "user32.dll,LockWorkStation"]]
    assert out == "Locked."


def test_volume_up_uses_sendkeys_175():
    run = FakeRun()
    out = sc.control("volume_up", run=run)
    assert run.commands[0][:3] == ["powershell.exe", "-NoProfile", "-Command"]
    assert "175" in run.commands[0][3]
    assert out == "Volume up."


@pytest.mark.parametrize("action,code", [
    ("volume_down", "174"),
    ("mute", "173"),
    ("play_pause", "179"),
    ("next_track", "176"),
    ("previous_track", "177"),
])
def test_media_and_volume_actions_send_expected_code(action, code):
    run = FakeRun()
    sc.control(action, run=run)
    assert code in run.commands[0][3]


def test_sleep_runs_setsuspendstate():
    run = FakeRun()
    out = sc.control("sleep", run=run)
    assert run.commands[0][0] == "rundll32.exe"
    assert "SetSuspendState" in run.commands[0][1]
    assert out == "Going to sleep."


def test_unknown_action_is_friendly_and_does_not_run():
    run = FakeRun()
    out = sc.control("format_c_drive", run=run)
    assert out == "I can't do that one."
    assert run.commands == []


def test_run_failure_is_friendly():
    run = FakeRun(raises=True)
    assert sc.control("lock", run=run) == "That didn't work on this machine."
