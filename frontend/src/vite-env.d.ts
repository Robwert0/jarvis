/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Absolute base URL of the FastAPI backend in packaged builds, e.g.
   *  "http://127.0.0.1:8000". Empty in dev (Vite proxy handles /jarvis). */
  readonly VITE_API_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
