import { useEffect, useState } from 'react'
import { deleteConversation, listConversations } from '../../shared/api'
import type { ConversationSummary } from '../../shared/types'

function ConversationsPane(): React.JSX.Element {
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    listConversations()
      .then(setConversations)
      .catch((err) => setError(String(err)))
  }, [])

  async function refresh(): Promise<void> {
    try {
      setConversations(await listConversations())
      setError('')
    } catch (err) {
      setError(String(err))
    }
  }

  async function handleDelete(conversation: ConversationSummary): Promise<void> {
    const title = conversation.title || '(untitled)'
    if (!confirm(`Delete conversation "${title}" and all its messages?`)) return
    try {
      await deleteConversation(conversation.id)
      refresh()
    } catch (err) {
      setError(String(err))
    }
  }

  return (
    <>
      <h2>Conversations</h2>
      {error && <p className="form-error">{error}</p>}
      <ul className="item-list">
        {conversations.map((c) => (
          <li key={c.id} className="item">
            <div className="item-info">
              {c.title || '(untitled)'}
              <span className="item-meta">{new Date(c.updated_at).toLocaleString()}</span>
            </div>
            <div className="item-actions">
              <button className="danger" onClick={() => handleDelete(c)}>
                Delete
              </button>
            </div>
          </li>
        ))}
      </ul>
      {conversations.length === 0 && !error && <p className="placeholder">No conversations.</p>}
    </>
  )
}

export default ConversationsPane
