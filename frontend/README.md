# Jarvis Desktop UI

A Discord/Steam-style desktop app for Jarvis, built with **Tauri v2 + React +
Vite (TypeScript)**. It's a thin native shell around a web UI that talks to the
existing FastAPI backend over the `/jarvis/*` HTTP API — the same endpoints the
old `app/static/` page used.

```
frontend/
├── src/                 # React app
│   ├── lib/api.ts       # typed client for the FastAPI backend
│   ├── components/       # TitleBar, Rail, ChatView, MacrosView, MemoryView
│   ├── styles/global.css # dark Discord/Steam theme
│   └── App.tsx
├── src-tauri/           # Rust/Tauri shell (window, config, icons)
└── vite.config.ts       # dev server on :1420, proxies /jarvis -> :8000
```

## Prerequisites

- **Node 18+** and npm
- **Rust** (stable) — https://rustup.rs
- **Tauri OS deps** — on Linux: `webkit2gtk-4.1`, `libgtk-3-dev`,
  `libappindicator3-dev`, `librsvg2-dev`, `patchelf`, `build-essential`.
  See https://tauri.app/start/prerequisites/ for the exact package list per OS.
  (On WSL2 you also need an X server / WSLg to see the window.)

## Develop

Two processes: the Python backend and the Tauri app.

```bash
# 1) Backend (from the repo root)
python -m app.main            # serves the API on http://127.0.0.1:8000

# 2) Desktop app (from frontend/)
npm install                   # first time only
npm run app                   # = tauri dev: launches the native window
```

`npm run app` runs `tauri dev`, which starts Vite (`:1420`) and opens the native
window. In dev, Vite proxies `/jarvis/*` to the backend on `:8000`, so no CORS
is involved.

Want just the web UI in a browser (no native shell)? `npm run dev` and open
http://localhost:1420 — the custom window controls hide automatically when the
Tauri runtime isn't present.

## Build a distributable app

```bash
npm run app:build             # = tauri build -> installers in src-tauri/target/release/bundle/
```

The packaged app loads from its own origin, so it hits the backend at
`VITE_API_BASE` (default in code is empty → set it for the build):

```bash
VITE_API_BASE=http://127.0.0.1:8000 npm run app:build
```

The backend already enables permissive CORS (single-user local trust model) so
the packaged webview can call it.

## Icons

The icon set in `src-tauri/icons/` is generated from `src-tauri/app-icon.png`.
To rebrand, replace that PNG (1024×1024) and regenerate:

```bash
npm run tauri icon src-tauri/app-icon.png
```

## Not built yet (deliberately)

- Backend-as-sidecar: right now you start `python -m app.main` yourself. A later
  step can have Tauri spawn/manage the backend via the shell plugin.
- Voice/wake-word wiring into this UI (the Python wake-word process is separate).
- Settings view.
