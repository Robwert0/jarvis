import { useEffect, useState } from 'react'
import { createMacro, deleteMacro, listMacros, updateMacro } from '../../shared/api'
import type { MacroView } from '../../shared/types'
import MacroEditor from './MacroEditor'
import { formatApps } from './macroText'

function MacrosPane(): React.JSX.Element {
  const [macros, setMacros] = useState<MacroView[]>([])
  const [editing, setEditing] = useState<string | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    refresh()
  }, [])

  async function refresh(): Promise<void> {
    try {
      setMacros(await listMacros())
      setError('')
    } catch (err) {
      setError(String(err))
    }
  }

  async function handleCreate(name: string, apps: MacroView['apps']): Promise<void> {
    await createMacro(name, apps)
    refresh()
  }

  async function handleUpdate(name: string, apps: MacroView['apps']): Promise<void> {
    await updateMacro(name, apps)
    setEditing(null)
    refresh()
  }

  async function handleDelete(name: string): Promise<void> {
    if (!confirm(`Delete macro "${name}"?`)) return
    try {
      await deleteMacro(name)
      refresh()
    } catch (err) {
      setError(String(err))
    }
  }

  return (
    <>
      <h2>Macros</h2>
      {error && <p className="form-error">{error}</p>}
      <ul className="item-list">
        {macros.map((m) =>
          editing === m.name ? (
            <li key={m.name} className="item">
              <MacroEditor
                initialName={m.name}
                initialApps={formatApps(m.apps)}
                nameLocked
                submitLabel="Save"
                onSubmit={(name, apps) => handleUpdate(name, apps)}
                onCancel={() => setEditing(null)}
              />
            </li>
          ) : (
            <li key={m.name} className="item">
              <div className="item-info">
                <strong>{m.name}</strong>
                <pre>{formatApps(m.apps)}</pre>
              </div>
              <div className="item-actions">
                <button onClick={() => setEditing(m.name)}>Edit</button>
                <button className="danger" onClick={() => handleDelete(m.name)}>
                  Delete
                </button>
              </div>
            </li>
          )
        )}
      </ul>
      {macros.length === 0 && !error && <p className="placeholder">No macros yet.</p>}
      <h2>New macro</h2>
      <MacroEditor submitLabel="Create" onSubmit={handleCreate} />
    </>
  )
}

export default MacrosPane
