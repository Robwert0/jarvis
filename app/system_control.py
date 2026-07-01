import subprocess

_PS = ["powershell.exe", "-NoProfile", "-Command"]


def _sendkeys(code):
    return _PS + [f"(New-Object -ComObject WScript.Shell).SendKeys([char]{code})"]


_COMMANDS = {
    "volume_up": (_sendkeys(175), "Volume up."),
    "volume_down": (_sendkeys(174), "Volume down."),
    "mute": (_sendkeys(173), "Muted."),
    "play_pause": (_sendkeys(179), "Toggled playback."),
    "next_track": (_sendkeys(176), "Next track."),
    "previous_track": (_sendkeys(177), "Previous track."),
    "lock": (["rundll32.exe", "user32.dll,LockWorkStation"], "Locked."),
    "sleep": (
        ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
        "Going to sleep.",
    ),
}


def _default_run(command):
    subprocess.run(command, check=True)


def control(action, *, run=None):
    entry = _COMMANDS.get((action or "").strip())
    if entry is None:
        return "I can't do that one."
    command, confirmation = entry
    run = run or _default_run
    try:
        run(command)
    except Exception:
        return "That didn't work on this machine."
    return confirmation
