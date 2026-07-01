import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Tauri expects a fixed dev port and doesn't want Vite clearing the screen.
export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
    // In dev, proxy API calls to the FastAPI backend so the browser/webview
    // and the API share an origin (no CORS needed). In a packaged Tauri build
    // the app hits VITE_API_BASE directly (see src/lib/api.ts).
    proxy: {
      "/jarvis": "http://127.0.0.1:8000",
    },
  },
  // Vite reads .env vars prefixed with VITE_.
  envPrefix: ["VITE_"],
});
