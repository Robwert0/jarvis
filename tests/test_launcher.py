import json
from types import SimpleNamespace

import pytest

from app import launcher


# --- helpers ----------------------------------------------------------------

APPS = [
    {"Name": "Photos", "AppID": "Microsoft.Windows.Photos_8wekyb!App"},
    {"Name": "Calculator", "AppID": "Microsoft.WindowsCalculator_8wekyb!App"},
    {"Name": "Google Chrome", "AppID": "Chrome.AppID"},
]


class FakeRun:
    """Stands in for subprocess.run. Branches on the powershell command:
    `Get-StartApps` returns the app list as JSON; anything else is treated as a
    Start-Process launch and returns the configured return code / stderr."""

    def __init__(self, returncode: int = 0, stderr: str = "") -> None:
        self.returncode = returncode
        self.stderr = stderr
        self.enumerate_calls = 0
        self.launch_commands: list[str] = []

    def __call__(self, cmd, capture_output=False, text=False):
        joined = " ".join(cmd)
        if "Get-StartApps" in joined:
            self.enumerate_calls += 1
            return SimpleNamespace(stdout=json.dumps(APPS), returncode=0, stderr="")
        self.launch_commands.append(joined)
        return SimpleNamespace(stdout="", returncode=self.returncode, stderr=self.stderr)


def fake_proc_version(*, exists: bool, text: str = ""):
    """Factory for app.launcher.Path so detect_platform() reads a controlled
    /proc/version (or a missing one)."""
    return lambda _arg: SimpleNamespace(exists=lambda: exists, read_text=lambda: text)


@pytest.fixture(autouse=True)
def reset_singleton():
    """get_launcher() caches a module-level instance; clear it between tests."""
    launcher._launcher = None
    yield
    launcher._launcher = None


@pytest.fixture
def fake_run(monkeypatch: pytest.MonkeyPatch) -> FakeRun:
    runner = FakeRun()
    monkeypatch.setattr(launcher.subprocess, "run", runner)
    return runner


# --- detect_platform --------------------------------------------------------

def test_detect_platform_wsl(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        launcher, "Path", fake_proc_version(exists=True, text="Linux ... microsoft ...")
    )
    monkeypatch.setattr(launcher.sys, "platform", "linux")
    assert launcher.detect_platform() == "wsl"


def test_detect_platform_native_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    # /proc/version exists but is not WSL -> raw sys.platform.
    monkeypatch.setattr(
        launcher, "Path", fake_proc_version(exists=True, text="Linux ... generic ...")
    )
    monkeypatch.setattr(launcher.sys, "platform", "linux")
    assert launcher.detect_platform() == "linux"


def test_detect_platform_windows_does_not_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    # Regression: /proc/version is absent off-Linux; reading it unconditionally
    # used to raise FileNotFoundError before the win32 branch was reached.
    monkeypatch.setattr(launcher, "Path", fake_proc_version(exists=False))
    monkeypatch.setattr(launcher.sys, "platform", "win32")
    assert launcher.detect_platform() == "win32"


def test_detect_platform_macos_does_not_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(launcher, "Path", fake_proc_version(exists=False))
    monkeypatch.setattr(launcher.sys, "platform", "darwin")
    assert launcher.detect_platform() == "darwin"


# --- get_launcher -----------------------------------------------------------

@pytest.mark.parametrize("platform", ["win32", "wsl"])
def test_get_launcher_supported(monkeypatch: pytest.MonkeyPatch, platform: str) -> None:
    monkeypatch.setattr(launcher, "detect_platform", lambda: platform)
    assert isinstance(launcher.get_launcher(), launcher.WindowsLauncher)


def test_get_launcher_unsupported_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(launcher, "detect_platform", lambda: "linux")
    assert launcher.get_launcher() is None


def test_get_launcher_is_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(launcher, "detect_platform", lambda: "win32")
    assert launcher.get_launcher() is launcher.get_launcher()


# --- WindowsLauncher._installed_apps (caching) ------------------------------

def test_installed_apps_cached(fake_run: FakeRun) -> None:
    win = launcher.WindowsLauncher()
    first = win._installed_apps()
    second = win._installed_apps()
    assert first == [("Photos", APPS[0]["AppID"]),
                     ("Calculator", APPS[1]["AppID"]),
                     ("Google Chrome", APPS[2]["AppID"])]
    assert second is first            # same cached object
    assert fake_run.enumerate_calls == 1  # Get-StartApps ran only once


# --- WindowsLauncher.launch -------------------------------------------------

def test_launch_substring_match(fake_run: FakeRun) -> None:
    result = launcher.WindowsLauncher().launch("photos")
    assert result == "Opening Photos."
    assert APPS[0]["AppID"] in fake_run.launch_commands[0]


def test_launch_fuzzy_match(fake_run: FakeRun) -> None:
    # "calculater" is not a substring of any name but is a close typo.
    result = launcher.WindowsLauncher().launch("calculater")
    assert result == "Opening Calculator."
    assert APPS[1]["AppID"] in fake_run.launch_commands[0]


def test_launch_no_match_does_not_launch(fake_run: FakeRun) -> None:
    result = launcher.WindowsLauncher().launch("zzz")
    assert result.startswith("I couldn't find an app called zzz")
    assert fake_run.launch_commands == []  # nothing was launched


def test_launch_reports_powershell_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = FakeRun(returncode=1, stderr="boom")
    monkeypatch.setattr(launcher.subprocess, "run", runner)
    result = launcher.WindowsLauncher().launch("photos")
    assert result == "I couldn't open photos - boom."


# --- launch() top-level -----------------------------------------------------

def test_launch_unsupported_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(launcher, "detect_platform", lambda: "linux")
    assert launcher.launch("photos") == "Opening apps isn't wired up on this platform yet."
