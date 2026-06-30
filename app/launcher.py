import subprocess
import json
import difflib
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LaunchResult:
    ok: bool
    message: str


def detect_platform():
    proc_version = Path("/proc/version")
    if proc_version.exists() and "microsoft" in proc_version.read_text().lower():
        return "wsl"

    return sys.platform


class WindowsLauncher:
    def __init__(self):
        self._apps = None

    def _installed_apps(self):
        if self._apps is None:
            result = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-Command",
                    "Get-StartApps | ConvertTo-Json",
                ],
                capture_output=True,
                text=True,
            )
            data = json.loads(result.stdout)
            self._apps = [(d["Name"], d["AppID"]) for d in data]

        return self._apps

    def _resolve(self, name):
        """Best-match (display_name, appid) for a name, or None."""
        apps = self._installed_apps()
        app_name = name.strip().lower()
        hits = [(n, a) for n, a in apps if app_name in n.lower()]
        if hits:
            return min(hits, key=lambda pair: len(pair[0]))
        by_lower = {n.lower(): (n, a) for n, a in apps}
        close = difflib.get_close_matches(app_name, list(by_lower), n=1, cutoff=0.6)
        if close:
            return by_lower[close[0]]
        return None

    def launch(self, name):
        app_name = name.strip().lower()
        resolved = self._resolve(name)
        if resolved is None:
            apps = self._installed_apps()
            by_lower = {n.lower(): (n, a) for n, a in apps}
            suggestions = difflib.get_close_matches(
                app_name, list(by_lower), n=3, cutoff=0.4
            )
            hint = f"Did you mean: {', '.join(suggestions)}?" if suggestions else " "
            return LaunchResult(
                False, f"I couldn't find an app called {app_name}. {hint}"
            )
        display_name, appid = resolved
        res = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                f'Start-Process "shell:AppsFolder\\{appid}"',
            ],
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            return LaunchResult(True, f"Opening {display_name}.")
        return LaunchResult(False, f"I couldn't open {app_name} - {res.stderr.strip()}.")

    def is_running(self, name):
        resolved = self._resolve(name)
        if resolved is None:
            return False
        display_name, _ = resolved
        res = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "Get-Process | Where-Object { $_.MainWindowTitle } | "
                "Select-Object -ExpandProperty MainWindowTitle",
            ],
            capture_output=True,
            text=True,
        )
        return display_name.lower() in res.stdout.lower()


_launcher = None


def get_launcher():
    global _launcher
    if _launcher is None:
        platform = detect_platform()
        if platform == "win32" or platform == "wsl":
            _launcher = WindowsLauncher()
    return _launcher


def launch(app):
    launcher = get_launcher()
    if launcher is None:
        return LaunchResult(False, "Opening apps isn't wired up on this platform yet.")
    return launcher.launch(app)


def is_running(app):
    launcher = get_launcher()
    if launcher is None:
        return False
    return launcher.is_running(app)
