export type View = "chat" | "macros" | "memory";

const ITEMS: { id: View; label: string; glyph: string }[] = [
  { id: "chat", label: "Chat", glyph: "💬" },
  { id: "macros", label: "Macros", glyph: "⚡" },
  { id: "memory", label: "Memory", glyph: "🧠" },
];

export default function Rail({
  view,
  onChange,
}: {
  view: View;
  onChange: (v: View) => void;
}) {
  return (
    <nav className="rail">
      <div className="rail-logo" title="Jarvis">
        J
      </div>
      <div className="rail-items">
        {ITEMS.map((it) => (
          <button
            key={it.id}
            className={`rail-item ${view === it.id ? "active" : ""}`}
            title={it.label}
            onClick={() => onChange(it.id)}
          >
            <span className="rail-glyph">{it.glyph}</span>
          </button>
        ))}
      </div>
    </nav>
  );
}
