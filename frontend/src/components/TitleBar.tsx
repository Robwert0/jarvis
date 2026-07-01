import { useEffect, useState } from "react";

// Custom Discord/Steam-style title bar. The window is created with
// decorations:false (see tauri.conf.json), so we draw our own controls.
// Falls back to a plain draggable bar when running in a plain browser
// (no Tauri runtime), so `npm run dev` in a browser still works.

export default function TitleBar() {
  const [win, setWin] = useState<
    typeof import("@tauri-apps/api/window") | null
  >(null);

  useEffect(() => {
    let alive = true;
    // Only load the Tauri API when the runtime is present.
    if (typeof window !== "undefined" && "__TAURI_INTERNALS__" in window) {
      import("@tauri-apps/api/window").then((mod) => {
        if (alive) setWin(mod);
      });
    }
    return () => {
      alive = false;
    };
  }, []);

  const current = () => win?.getCurrentWindow();

  return (
    <header className="titlebar" data-tauri-drag-region>
      <div className="titlebar-brand" data-tauri-drag-region>
        <span className="titlebar-dot" />
        Jarvis
      </div>
      {win && (
        <div className="titlebar-controls">
          <button
            className="tb-btn"
            aria-label="Minimize"
            onClick={() => current()?.minimize()}
          >
            &#8211;
          </button>
          <button
            className="tb-btn"
            aria-label="Maximize"
            onClick={() => current()?.toggleMaximize()}
          >
            &#9633;
          </button>
          <button
            className="tb-btn tb-close"
            aria-label="Close"
            onClick={() => current()?.close()}
          >
            &#10005;
          </button>
        </div>
      )}
    </header>
  );
}
