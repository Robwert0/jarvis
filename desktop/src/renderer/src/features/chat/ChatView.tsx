import { useEffect, useRef, useState } from 'react'
import { getConversation, listConversations, sendChat } from '../../shared/api'
import type { ActionView, ConversationSummary } from '../../shared/types'
import { useVoice } from './useVoice'

const VOICE_LABELS = {
  idle: '🎤 Voice',
  connecting: '… Connecting',
  listening: '🟢 Listening',
  speaking: '🔵 Speaking'
} as const

type TranscriptItem =
  { kind: 'message'; role: string; content: string } | { kind: 'actions'; actions: ActionView[] }

function ChatView(): React.JSX.Element {
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [items, setItems] = useState<TranscriptItem[]>([])
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const transcriptRef = useRef<HTMLDivElement>(null)
  const voice = useVoice({
    onMessage: (role, content) => setItems((prev) => [...prev, { kind: 'message', role, content }]),
    onError: (message) =>
      setItems((prev) => [...prev, { kind: 'message', role: 'error', content: message }])
  })

  useEffect(() => {
    refreshConversations()
  }, [])

  useEffect(() => {
    const el = transcriptRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [items, sending])

  async function refreshConversations(): Promise<void> {
    try {
      setConversations(await listConversations())
    } catch {
      setConversations([])
    }
  }

  async function openConversation(id: string): Promise<void> {
    try {
      const messages = await getConversation(id)
      setSessionId(id)
      setItems(messages.map((m) => ({ kind: 'message', role: m.role, content: m.content })))
    } catch (err) {
      setItems([{ kind: 'message', role: 'error', content: String(err) }])
    }
  }

  function startNewChat(): void {
    setSessionId(null)
    setItems([])
  }

  async function handleSend(e: React.FormEvent): Promise<void> {
    e.preventDefault()
    const message = draft.trim()
    if (!message || sending) return
    setDraft('')
    setItems((prev) => [...prev, { kind: 'message', role: 'user', content: message }])
    setSending(true)
    try {
      const res = await sendChat(message, sessionId)
      setSessionId(res.session_id)
      setItems((prev) => [
        ...prev,
        ...(res.actions.length ? [{ kind: 'actions' as const, actions: res.actions }] : []),
        { kind: 'message', role: 'assistant', content: res.reply }
      ])
      refreshConversations()
    } catch (err) {
      setItems((prev) => [...prev, { kind: 'message', role: 'error', content: String(err) }])
    } finally {
      setSending(false)
    }
  }

  return (
    <section className="chat">
      <aside className="conversations">
        <button className="new-chat" onClick={startNewChat}>
          + New chat
        </button>
        <ul>
          {conversations.map((c) => (
            <li
              key={c.id}
              className={c.id === sessionId ? 'active' : ''}
              onClick={() => openConversation(c.id)}
            >
              {c.title || '(untitled)'}
            </li>
          ))}
        </ul>
      </aside>
      <div className="chat-pane">
        <div className="transcript" ref={transcriptRef}>
          {items.length === 0 && !sending && (
            <p className="placeholder">Say something to Jarvis.</p>
          )}
          {items.map((item, i) =>
            item.kind === 'message' ? (
              <div key={i} className={`msg ${item.role}`}>
                {item.content}
              </div>
            ) : (
              <div key={i} className="chips">
                {item.actions.map((a, j) => (
                  <span key={j} className="chip">
                    {a.tool}: {a.summary}
                  </span>
                ))}
              </div>
            )
          )}
          {sending && <div className="msg assistant pending">…</div>}
        </div>
        <form className="composer" onSubmit={handleSend}>
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Message Jarvis…"
            autoFocus
          />
          <button
            type="button"
            className={`voice ${voice.status}`}
            onClick={voice.toggle}
            disabled={voice.status === 'connecting'}
          >
            {VOICE_LABELS[voice.status]}
          </button>
          <button type="submit" disabled={sending || !draft.trim()}>
            Send
          </button>
        </form>
      </div>
    </section>
  )
}

export default ChatView
