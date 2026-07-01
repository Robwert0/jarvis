import { useState } from "react";
import TitleBar from "./components/TitleBar";
import Rail, { type View } from "./components/Rail";
import ChatView from "./components/ChatView";
import MacrosView from "./components/MacrosView";
import MemoryView from "./components/MemoryView";

export default function App() {
  const [view, setView] = useState<View>("chat");

  return (
    <div className="app">
      <TitleBar />
      <div className="body">
        <Rail view={view} onChange={setView} />
        {view === "chat" && <ChatView />}
        {view === "macros" && <MacrosView />}
        {view === "memory" && <MemoryView />}
      </div>
    </div>
  );
}
