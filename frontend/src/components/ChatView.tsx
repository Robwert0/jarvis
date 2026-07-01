import { useEffect, useRef, useState } from "react";
import {
  api,
  type ChatResponse,
  type ConversationSummary,
  type Message,
} from "../lib/api";

interface Turn {
  role: "user" | "assistant";
  content: string;
  actions?: ChatResponse["actions"];
}

export default function ChatView() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const scroller = useRef<HTMLDivElement>(null);

  const refreshConversations = () =>
    api.listConversations().then(setConversations).catch(() => {});

  useEffect(() => {
    refreshConversations();
  }, []);

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight });
  }, [turns]);

  async function openConversation(id: string) {
    setSessionId(id);
    try {
      const msgs: Message[] = await api.getConversation(id);
      setTurns(msgs.map((m) => ({ role: m.role as Turn["role"], content: m.content })));
    } catch {
      setTurns([]);
    }
  }

  function newChat() {
    setSessionId(null);
    setTurns([]);
  }

  async function removeConversation(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    await api.deleteConversation(id).catch(() => {});
    if (id === sessionId) newChat();
    refreshConversations();
  }

  async function send() {
    const message = input.trim();
    if (!message || sending) return;
    setInput("");
    setTurns((t) => [...t, { role: "user", content: message }]);
    setSending(true);
    try {
      const data = await api.chat(message, sessionId);
      setSessionId(data.session_id);
      setTurns((t) => [
        ...t,
        { role: "assistant", content: data.reply, actions: data.actions },
      ]);
      refreshConversations();
    } catch (err) {
      setTurns((t) => [
        ...t,
        { role: "assistant", content: `⚠️ ${(err as Error).message}` },
      ]);
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      <aside className="sidebar">
        <div className="sidebar-header">
          <span>Conversations</span>
          <button className="ghost-btn" onClick={newChat}>
            + New
          </button>
        </div>
        <ul className="conv-list">
          {conversations.map((c) => (
            <li
              key={c.id}
              className={`conv-item ${c.id === sessionId ? "active" : ""}`}
              onClick={() => openConversation(c.id)}
            >
              <span className="conv-title">{c.title || "(untitled)"}</span>
              <button
                className="conv-del"
                title="Delete"
                onClick={(e) => removeConversation(c.id, e)}
              >
                ✕
              </button>
            </li>
          ))}
          {conversations.length === 0 && (
            <li className="empty">No conversations yet</li>
          )}
        </ul>
      </aside>

      <section className="content">
        <div className="messages" ref={scroller}>
          {turns.length === 0 && (
            <div className="welcome">
              <h1>Good to see you.</h1>
              <p>Ask Jarvis to open an app, run a macro, or just talk.</p>
            </div>
          )}
          {turns.map((t, i) => (
            <div key={i} className={`bubble-row ${t.role}`}>
              <div className={`bubble ${t.role}`}>
                {t.content}
                {t.actions && t.actions.length > 0 && (
                  <div className="chips">
                    {t.actions.map((a, j) => (
                      <span className="chip" key={j}>
                        {a.tool}: {a.summary}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          {sending && (
            <div className="bubble-row assistant">
              <div className="bubble assistant typing">Jarvis is thinking…</div>
            </div>
          )}
        </div>

        <form
          className="composer"
          onSubmit={(e) => {
            e.preventDefault();
            send();
          }}
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Message Jarvis…"
            autoComplete="off"
          />
          <button type="submit" disabled={sending || !input.trim()}>
            Send
          </button>
        </form>
      </section>
    </>
  );
}
