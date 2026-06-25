# Stage 3: `open_app` — universal app launcher

Status: **Designed** (2026-06-25). First Stage-3 client tool (roadmap item 3 in
`CLAUDE.md`; architecture in `docs/voice-architecture.md`). `open_app` is an
ElevenLabs client tool that launches an installed application on the user's
machine, by name, on whatever OS the executor is running.

## Goal
"Jarvis, open Spotify" → the app opens on the user's computer. Works for any
installed app (no curated list), and is portable across OSes — the executor
detects its host and launches appropriately. First and only backend built now:
Windows (incl. WSL→Windows interop), the one platform we can currently test.

## Architecture — three layers, one job each
```
app/voice.py     runner: builds the Conversation, attaches client tools
   | uses
app/tools.py     adapter: thin ElevenLabs client-tool handlers
   | uses
app/launcher.py  core: "open one app on this host", reusable
```
Rule: launch logic lives in `launcher.py`; tools are thin wrappers. A future
`open_work_environment` macro (Stage 4) loops over `launcher.launch()` and never
touches ElevenLabs wiring.

## Launcher core (`app/launcher.py`)
Public surface:
- `launch(app: str) -> str` — the only entry point tools/macros call; returns a
  human-readable result that becomes Claude's spoken feedback.
- `detect_platform() -> str` — "windows" | "wsl" | "macos" | "linux". WSL reports
  "linux" via `sys.platform`, so we also check `/proc/version` for "microsoft".
- `get_launcher() -> Launcher | None` — backend for the host, or None if unsupported.

Backends share a `Launcher` interface (`.launch(app) -> str`). Implemented:
`WindowsLauncher` (covers WSL→Windows and native Windows; both reach
`powershell.exe`). macOS/Linux: interface ready, not implemented → `launch()`
returns "not wired up on this platform yet".

### Dynamic app resolution (no hardcoded list)
Each OS already indexes installed apps; we enumerate → match → launch:
- Windows: `Get-StartApps` → (Name, AppID) for every Start-Menu app (desktop +
  Store). Launch via `Start-Process "shell:AppsFolder\<AppID>"`.
- macOS (later): `open -a "Name"` resolves by name.
- Linux (later): `.desktop` files + `gtk-launch`.

`WindowsLauncher`:
- `_installed_apps()` — `Get-StartApps` output, fetched once and cached per session.
- `launch(app)` — normalize + fuzzy-match against installed names; open the best
  confident match and announce it; on no match return "couldn't find 'x' — did
  you mean …".

### Matching
Normalize (lowercase/strip), then closest-match (`difflib`) + substring, so
"vs code" → "Visual Studio Code" and "chrome" → "Google Chrome". Start simple,
tune against real names. On a fuzzy match, **open the best match and announce
what was opened** (Option A — fewer voice turns; a mistake is spoken back and
easily corrected). Reserve confirmation for genuine ties.

## Security model
The `app` argument originates from voice → STT → Claude, so it is untrusted. Rule:
the spoken name only drives a *search* against the system-provided app list; we
launch the resolved `AppID` from that list, never the raw string as a command.
Untrusted text selects from a trusted menu; it never reaches the shell as a command.

## Two-sided registration
- ElevenLabs agent (dashboard): declare a client tool `open_app`, description
  "Open an application on the user's computer", parameter `app` (string, required).
- Local code: `app/tools.py` `build_client_tools()` registers the Python `open_app`;
  `app/voice.py` passes `client_tools=build_client_tools()` to `Conversation(...)`.

`open_app(params)` extracts `app`, delegates to `launcher.launch(app)`, and always
returns a string.

## Error handling
The handler never raises (a raised exception breaks the tool result):
- Missing/empty `app` → "Which app should I open?"
- No match → "I couldn't find an app called 'foo'. Did you mean: …?"
- Unsupported platform → "Opening apps isn't wired up on this platform yet."
- Launch failure → "I couldn't open Spotify — <reason>." Report actual state,
  never fake success.

## Testing (`tests/test_launcher.py`, CI-safe)
`subprocess` and `Get-StartApps` mocked; nothing actually launches:
- `detect_platform()` → "wsl" when `/proc/version` contains "microsoft"; other branches.
- known/fuzzy name → matches the right `AppID`, returns "Opened <name>".
- unknown name → "did you mean" message, no launch.
- unsupported platform → "not wired up" message.
- `open_app({})` → "Which app should I open?"

## Deliberately deferred (YAGNI)
- macOS / native-Linux backends (no test machine) — interface ready, stubbed.
- `open_work_environment` macros — Stage 4; `launch()` is the reuse hook.
- Idempotency / focus-if-already-running — Stage 4.
- Config-file / alias registry — add only if matching gaps appear.
- Interruption/cancellation — `open_app` is instant/irreversible; the spike +
  cancellation land with composite actions (Stage 4).
