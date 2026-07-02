import ConversationsPane from './ConversationsPane'
import MacrosPane from './MacrosPane'
import MemoriesPane from './MemoriesPane'

function ManageView(): React.JSX.Element {
  return (
    <section className="view">
      <h1>Manage</h1>
      <MacrosPane />
      <MemoriesPane />
      <ConversationsPane />
    </section>
  )
}

export default ManageView
