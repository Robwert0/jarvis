import { useEffect, useState } from 'react'
import ChatView from './features/chat/ChatView'
import ManageView from './features/manage/ManageView'
import { getMemories } from './shared/api'

type View = 'chat' | 'manage'

function App(): React.JSX.Element {
  const [view, setView] = useState<View>('chat')
  const [backend, setBackend] = useState('checking backend…')

  useEffect(() => {
    getMemories()
      .then((memories) => setBackend(`backend online — ${memories.length} memories`))
      .catch(() => setBackend('backend offline — start FastAPI on :8000'))
  }, [])

  return (
    <div className="app">
      <nav className="sidebar">
        <div className="brand">Jarvis</div>
        <button className={view === 'chat' ? 'active' : ''} onClick={() => setView('chat')}>
          Chat
        </button>
        <button className={view === 'manage' ? 'active' : ''} onClick={() => setView('manage')}>
          Manage
        </button>
        <div className="status">{backend}</div>
      </nav>
      <main>{view === 'chat' ? <ChatView /> : <ManageView />}</main>
    </div>
  )
}

export default App
