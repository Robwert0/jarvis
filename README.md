# jarvis

Voice-controlled personal AI assistant inspired by Iron Man's Jarvis — a
**desktop app** (Electron + React + TypeScript) backed by a FastAPI + Claude
agent. Talk to it or type to it: it opens apps, runs macros, searches the web,
controls the system, and remembers things about you. Single-user, runs locally.

## What Jarvis can do today

- **Desktop app.** A Discord-style Electron app (`desktop/`) with a chat view
  (conversation history, action chips, composer) and a Manage view for macros.
- **Hold a voice conversation — in the app.** Press 🎤 and talk: an ElevenLabs
  Conversational AI session runs in the renderer with turn-taking and barge-in.
  Voice transcripts are persisted like text chats, and saved memories are
  bridged into every session. The standalone Python voice loop
  (`python -m app.voice`) and the Porcupine wake word (`python -m app.wake`)
  still work headless.
- **Act on the machine.** Six tools, shared by the text and voice paths:
  `open_app` (fuzzy name matching), `run_macro` (multi-app launches with
  per-app args), `cancel_action` (cooperative, LLM-driven cancellation),
  `remember` (long-term memory), `search_web` (Tavily), `control_system`
  (volume / media / lock / sleep from WSL → Windows).
- **Remember across sessions.** Facts saved via `remember` live in SQLite and
  are injected into every text chat and every voice session.
- **Chat over HTTP.** `/jarvis/chat` runs a server-side Claude tool-use loop;
  a management API covers macro CRUD plus memory and conversation pruning.
  OpenAPI docs at `/docs`. The legacy browser page at `http://127.0.0.1:8000`
  remains as a fallback.

## Architecture

```
desktop/  Electron + React + TS app ──HTTP──▶ FastAPI (app/) ──▶ Claude (agent loop)
   │                                              │
   └──WebSocket──▶ ElevenLabs Agent ──client tools─┘ (executed in the Python process)
```

Two LLM paths share one toolset: the ElevenLabs Agent's LLM drives the voice
loop; a server-side Claude loop (`app/agent.py`) drives text chat. Voice
rationale: [`docs/voice-architecture.md`](docs/voice-architecture.md).

## Status

Feature-complete for daily use (2026-07-02). All stages shipped:

| Capability | Status |
|------------|--------|
| Text `/chat` endpoint (Claude tool-use loop, multi-turn history) | ✅ |
| Voice loop via ElevenLabs Agent + Claude | ✅ |
| Local client tools (`open_app`, …) | ✅ |
| Cancellation of in-flight actions (cooperative token) | ✅ |
| Macros: storage, cancellable runner, management API + UI | ✅ |
| Web search + system control tools | ✅ |
| Wake word (Porcupine "Jarvis", headless path) | ✅ |
| Desktop app: chat, voice, macro management | ✅ |

Not built (by choice): multi-user/auth (single-user pivot), observability,
eval harness. Open ideas: Memories/Conversations panes in Manage, in-app wake
word (Porcupine WASM), tray/autostart, packaged Windows installer.

## Stack

- **Desktop:** Electron + React + TypeScript (electron-vite), `desktop/`
- **Backend:** FastAPI (Python 3.12), `app/`
- **LLM:** Claude (Anthropic) — ElevenLabs Agent LLM (voice) + server-side loop (text)
- **Voice (STT + TTS + turn-taking + barge-in):** ElevenLabs Agents
- **Wake word:** Porcupine ("jarvis")
- **Storage:** SQLite (`jarvis.db`: conversations, messages, memories; `macros.db`)

## Getting started

```bash
# backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # ANTHROPIC_API_KEY, ELEVENLABS_API_KEY, ELEVENLABS_AGENT_ID, TAVILY_API_KEY, PICOVOICE_ACCESS_KEY
uvicorn app.main:app --port 8000

# desktop app (separate terminal)
cd desktop
npm install
npm run dev

pytest                           # backend test suite
npm run typecheck && npm run lint  # desktop checks (run inside desktop/)
```

Notes:
- On a fresh WSL distro, Electron needs `sudo apt-get install -y libnss3 libnspr4`.
- Voice tools must be declared as **client tools** on the ElevenLabs agent
  (dashboard → Tools): `remember(fact)`, `open_app(app)`, `run_macro(macro)`,
  `cancel_action()`, `search_web(query)`, `control_system(action)` — enable
  "wait for response" and raise the response timeout.
- The API binds to localhost only — it can run real actions on the machine.
