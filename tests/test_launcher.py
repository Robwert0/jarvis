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
        self.window_titles: list[str] = []  # MainWindowTitle lines Get-Process returns

    def __call__(self, cmd, capture_output=False, text=False):
        joined = " ".join(cmd)
        if "Get-StartApps" in joined:
            self.enumerate_calls += 1
            return SimpleNamespace(stdout=json.dumps(APPS), returncode=0, stderr="")
        if "Get-Process" in joined:
            return SimpleNamespace(
                stdout="\n".join(self.window_titles), returncode=0, stderr=""
            )
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
    assert result.ok is True
    assert result.message == "Opening Photos."
    assert APPS[0]["AppID"] in fake_run.launch_commands[0]


def test_launch_fuzzy_match(fake_run: FakeRun) -> None:
    # "calculater" is not a substring of any name but is a close typo.
    result = launcher.WindowsLauncher().launch("calculater")
    assert result.ok is True
    assert result.message == "Opening Calculator."
    assert APPS[1]["AppID"] in fake_run.launch_commands[0]


def test_launch_no_match_does_not_launch(fake_run: FakeRun) -> None:
    result = launcher.WindowsLauncher().launch("zzz")
    assert result.ok is False
    assert result.message.startswith("I couldn't find an app called zzz")
    assert fake_run.launch_commands == []  # nothing was launched


def test_launch_reports_powershell_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = FakeRun(returncode=1, stderr="boom")
    monkeypatch.setattr(launcher.subprocess, "run", runner)
    result = launcher.WindowsLauncher().launch("photos")
    assert result.ok is False
    assert result.message == "I couldn't open photos - boom."


def test_launch_with_args_uses_argumentlist(fake_run: FakeRun) -> None:
    # An app launched with args goes via Start-Process -FilePath <AppID>
    # -ArgumentList ... (App Paths resolves the AppID), not shell:AppsFolder.
    result = launcher.WindowsLauncher().launch(
        "chrome", ["--profile-directory=Profile 1"]
    )
    assert result.ok is True
    assert result.message == "Opening Google Chrome."
    cmd = fake_run.launch_commands[0]
    assert "Start-Process -FilePath" in cmd
    assert APPS[2]["AppID"] in cmd                  # "Chrome.AppID" (the resolved AppID)
    assert "--profile-directory=Profile 1" in cmd
    assert "shell:AppsFolder" not in cmd


def test_launch_no_args_still_uses_appsfolder(fake_run: FakeRun) -> None:
    launcher.WindowsLauncher().launch("photos")
    assert "shell:AppsFolder" in fake_run.launch_commands[0]
    assert "-ArgumentList" not in fake_run.launch_commands[0]


# --- WindowsLauncher.is_running ---------------------------------------------

def test_is_running_true_when_window_title_matches(fake_run: FakeRun) -> None:
    fake_run.window_titles = ["index.js - Google Chrome", "Settings"]
    assert launcher.WindowsLauncher().is_running("chrome") is True


def test_is_running_false_when_no_match(fake_run: FakeRun) -> None:
    fake_run.window_titles = ["Settings"]
    assert launcher.WindowsLauncher().is_running("chrome") is False


def test_is_running_false_when_app_unknown(fake_run: FakeRun) -> None:
    # name resolves to nothing -> biased to False (so caller launches)
    assert launcher.WindowsLauncher().is_running("zzz") is False


def test_top_level_is_running_unsupported_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(launcher, "detect_platform", lambda: "linux")
    assert launcher.is_running("photos") is False


# --- launch() top-level -----------------------------------------------------

def test_launch_unsupported_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(launcher, "detect_platform", lambda: "linux")
    result = launcher.launch("photos")
    assert result.ok is False
    assert result.message == "Opening apps isn't wired up on this platform yet."
