import subprocess
import json
import difflib
import sys
from pathlib import Path


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

    def launch(self, name):
        apps = self._installed_apps()
        app_name = name.strip().lower()
        hits = [(name, appid) for name, appid in apps if app_name in name.lower()]
        if hits:
            name, appid = min(hits, key=lambda pair: len(pair[0]))
        else:
            by_lower = {name.lower(): (name, appid) for name, appid in apps}
            close = difflib.get_close_matches(app_name, list(by_lower), n=1, cutoff=0.6)
            if close:
                name, appid = by_lower[close[0]]
            else:
                suggestions = difflib.get_close_matches(
                    app_name, list(by_lower), n=3, cutoff=0.4
                )
                hint = (
                    f"Did you mean: {', '.join(suggestions)}?" if suggestions else " "
                )
                return f"I couldn't find an app called {app_name}. {hint}"

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
            return f"Opening {name}."
        return f"I couldn't open {app_name} - {res.stderr.strip()}."


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
        return "Opening apps isn't wired up on this platform yet."
    return launcher.launch(app)
