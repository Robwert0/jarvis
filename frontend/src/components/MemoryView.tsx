import { useEffect, useState } from "react";
import { api, type MemoryView as Memory } from "../lib/api";

export default function MemoryView() {
  const [memories, setMemories] = useState<Memory[]>([]);

  const refresh = () => api.listMemories().then(setMemories).catch(() => {});

  useEffect(() => {
    refresh();
  }, []);

  async function remove(id: number) {
    await api.deleteMemory(id).catch(() => {});
    refresh();
  }

  return (
    <>
      <aside className="sidebar">
        <div className="sidebar-header">
          <span>Memory</span>
        </div>
        <p className="sidebar-note">Things Jarvis remembers about you.</p>
      </aside>

      <section className="content pad">
        <h1 className="view-title">🧠 Memory</h1>
        <div className="mem-list">
          {memories.map((m) => (
            <div className="card mem-card" key={m.id}>
              <span>{m.content}</span>
              <button className="ghost-btn danger" onClick={() => remove(m.id)}>
                Forget
              </button>
            </div>
          ))}
          {memories.length === 0 && (
            <div className="empty">Nothing remembered yet</div>
          )}
        </div>
      </section>
    </>
  );
}
