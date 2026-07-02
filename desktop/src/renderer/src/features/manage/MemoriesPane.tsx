import { useEffect, useState } from 'react'
import { deleteMemory, getMemories } from '../../shared/api'
import type { MemoryView } from '../../shared/types'

function MemoriesPane(): React.JSX.Element {
  const [memories, setMemories] = useState<MemoryView[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    refresh()
  }, [])

  async function refresh(): Promise<void> {
    try {
      setMemories(await getMemories())
      setError('')
    } catch (err) {
      setError(String(err))
    }
  }

  async function handleDelete(memory: MemoryView): Promise<void> {
    if (!confirm(`Forget "${memory.content}"?`)) return
    try {
      await deleteMemory(memory.id)
      refresh()
    } catch (err) {
      setError(String(err))
    }
  }

  return (
    <>
      <h2>Memories</h2>
      {error && <p className="form-error">{error}</p>}
      <ul className="item-list">
        {memories.map((m) => (
          <li key={m.id} className="item">
            <div className="item-info">
              {m.content}
              <span className="item-meta">{new Date(m.created_at).toLocaleString()}</span>
            </div>
            <div className="item-actions">
              <button className="danger" onClick={() => handleDelete(m)}>
                Forget
              </button>
            </div>
          </li>
        ))}
      </ul>
      {memories.length === 0 && !error && (
        <p className="placeholder">Nothing remembered yet — tell Jarvis to remember something.</p>
      )}
    </>
  )
}

export default MemoriesPane
