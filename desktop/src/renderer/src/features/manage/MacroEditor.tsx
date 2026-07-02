import { useState } from 'react'
import { parseApps } from './macroText'
import type { MacroAppEntry } from '../../shared/types'

interface MacroEditorProps {
  initialName?: string
  initialApps?: string
  nameLocked?: boolean
  submitLabel: string
  onSubmit: (name: string, apps: MacroAppEntry[]) => Promise<void>
  onCancel?: () => void
}

function MacroEditor({
  initialName = '',
  initialApps = '',
  nameLocked = false,
  submitLabel,
  onSubmit,
  onCancel
}: MacroEditorProps): React.JSX.Element {
  const [name, setName] = useState(initialName)
  const [appsText, setAppsText] = useState(initialApps)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function handleSubmit(e: React.FormEvent): Promise<void> {
    e.preventDefault()
    const apps = parseApps(appsText)
    if (!name.trim() || !apps.length) {
      setError('A macro needs a name and at least one app.')
      return
    }
    setBusy(true)
    setError('')
    try {
      await onSubmit(name.trim(), apps)
      setName(initialName)
      setAppsText(initialApps)
    } catch (err) {
      setError(String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="macro-editor" onSubmit={handleSubmit}>
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Macro name (e.g. work)"
        disabled={nameLocked}
      />
      <textarea
        value={appsText}
        onChange={(e) => setAppsText(e.target.value)}
        placeholder={
          'One app per line, extra words become args:\nchrome --profile-directory=Default\nspotify'
        }
        rows={4}
      />
      {error && <p className="form-error">{error}</p>}
      <div className="editor-actions">
        <button type="submit" disabled={busy}>
          {submitLabel}
        </button>
        {onCancel && (
          <button type="button" className="secondary" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
    </form>
  )
}

export default MacroEditor
