export interface ActionView {
  tool: string
  summary: string
}

export interface ConversationSummary {
  id: string
  title: string
  updated_at: string
}

export interface Message {
  role: string
  content: string
}

export interface ChatResponse {
  reply: string
  session_id: string
  model: string
  input_tokens: number
  output_tokens: number
  actions: ActionView[]
}

export interface MacroAppObject {
  app: string
  args: string[]
}

export type MacroAppEntry = string | MacroAppObject

export interface MacroView {
  name: string
  apps: MacroAppEntry[]
}

export interface MemoryView {
  id: number
  content: string
  created_at: string
}
