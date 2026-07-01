import { useEffect, useState } from "react";
import { api, type MacroAppEntry, type MacroView } from "../lib/api";

function appLabel(entry: MacroAppEntry): string {
  if (typeof entry === "string") return entry;
  return entry.args.length ? `${entry.app} ${entry.args.join(" ")}` : entry.app;
}

export default function MacrosView() {
  const [macros, setMacros] = useState<MacroView[]>([]);
  const [name, setName] = useState("");
  const [apps, setApps] = useState("");
  const [error, setError] = useState<string | null>(null);

  const refresh = () => api.listMacros().then(setMacros).catch(() => {});

  useEffect(() => {
    refresh();
  }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const list = apps
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    if (!name.trim() || list.length === 0) {
      setError("Give the macro a name and at least one app.");
      return;
    }
    try {
      await api.createMacro(name.trim(), list);
      setName("");
      setApps("");
      refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function remove(macroName: string) {
    await api.deleteMacro(macroName).catch(() => {});
    refresh();
  }

  return (
    <>
      <aside className="sidebar">
        <div className="sidebar-header">
          <span>Macros</span>
        </div>
        <p className="sidebar-note">
          Composite actions — launch several apps at once.
        </p>
      </aside>

      <section className="content pad">
        <h1 className="view-title">⚡ Macros</h1>

        <form className="card form" onSubmit={create}>
          <h3>New macro</h3>
          <label>
            Name
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="work-setup"
            />
          </label>
          <label>
            Apps (comma-separated)
            <input
              value={apps}
              onChange={(e) => setApps(e.target.value)}
              placeholder="code, chrome, slack"
            />
          </label>
          {error && <div className="form-error">{error}</div>}
          <button type="submit">Create</button>
        </form>

        <div className="macro-grid">
          {macros.map((m) => (
            <div className="card macro-card" key={m.name}>
              <div className="macro-card-head">
                <strong>{m.name}</strong>
                <button className="ghost-btn danger" onClick={() => remove(m.name)}>
                  Delete
                </button>
              </div>
              <ul className="macro-apps">
                {m.apps.map((a, i) => (
                  <li key={i}>{appLabel(a)}</li>
                ))}
              </ul>
            </div>
          ))}
          {macros.length === 0 && <div className="empty">No macros yet</div>}
        </div>
      </section>
    </>
  );
}
