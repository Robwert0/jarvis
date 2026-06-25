# jarvis

Voice-controlled personal AI assistant inspired by Iron Man's Jarvis. Talk to it,
and it talks back — opens apps, controls smart home devices, answers questions, and
automates tasks. Powered by Claude, FastAPI, and TypeScript.

## What Jarvis can do today

- **Hold a voice conversation.** A full voice loop (mic → speech-to-text → Claude →
  text-to-speech → speaker) runs through an ElevenLabs Agent with Claude as its
  brain, including turn-taking and barge-in. Run it with `python -m app.voice`.
- **Open apps by voice.** Say *"Jarvis, open Photos"* and it launches the app on
  your machine. Works for any installed app by name (no hardcoded list) with fuzzy
  matching, so *"open chrome"* finds *"Google Chrome"*. Backend implemented for
  Windows and WSL → Windows; macOS/Linux interfaces are stubbed for later.
- **Chat over HTTP.** A text-in/text-out `/jarvis/chat` endpoint (FastAPI) backed by
  Claude, with multi-turn conversation history. Kept as a text fallback and the
  basis for a future custom-LLM proxy. Run the API with `uvicorn app.main:app --reload`.

## Roadmap

Building Jarvis in stages. The voice loop is owned by ElevenLabs Agents; rationale
is in [`docs/voice-architecture.md`](docs/voice-architecture.md).

| Stage | Capability | Status |
|-------|------------|--------|
| 1 | Text `/chat` endpoint (Claude, multi-turn history) | ✅ Done |
| 2 | Voice loop via ElevenLabs Agent + Claude | ✅ Done |
| 3 | Local client-tool executor — first tool: `open_app` | ✅ Done |
| 4 | Composite actions / macros (e.g. `open_work_environment`) | ⏳ Next |
| 5 | Interruption vs. in-flight-action handling + cancellation | 🔜 Planned |
| 6 | More tools — web search, smart home, and beyond | 🔜 Planned |
| 7 | Wake-word activation (evaluate ElevenLabs vs. Porcupine) | 🔜 Planned |
| 8 | UI polish | 🔜 Planned |

## Stack

- **Backend:** FastAPI (Python 3.12)
- **LLM:** Claude (Anthropic), running as the ElevenLabs Agent's LLM
- **Voice (STT + TTS + turn-taking + barge-in):** ElevenLabs Agents
- **Local actions:** ElevenLabs client tools executed on-device via the Python SDK
- **Frontend:** TypeScript
- **Storage:** SQLite when needed

## Getting started

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in ANTHROPIC_API_KEY, ELEVENLABS_API_KEY, ELEVENLABS_AGENT_ID

python -m app.voice              # talk to Jarvis
uvicorn app.main:app --reload    # or use the text /jarvis/chat endpoint
pytest                           # run the test suite
```
