import type { ChatResponse, ConversationSummary, MemoryView, Message } from './types'

const BASE_URL = 'http://localhost:8000'

export class ApiError extends Error {
  constructor(
    public status: number,
    detail: string
  ) {
    super(detail)
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...(init?.body ? { headers: { 'Content-Type': 'application/json' } } : {}),
    ...init
  })
  if (!res.ok) {
    const detail = await res
      .json()
      .then((body) => body.detail ?? res.statusText)
      .catch(() => res.statusText)
    throw new ApiError(res.status, String(detail))
  }
  return res.status === 204 ? (undefined as T) : res.json()
}

export function getMemories(): Promise<MemoryView[]> {
  return request<MemoryView[]>('/jarvis/memories')
}

export function sendChat(message: string, sessionId: string | null): Promise<ChatResponse> {
  return request<ChatResponse>('/jarvis/chat', {
    method: 'POST',
    body: JSON.stringify({ message, session_id: sessionId })
  })
}

export function listConversations(): Promise<ConversationSummary[]> {
  return request<ConversationSummary[]>('/jarvis/conversations')
}

export function getConversation(sessionId: string): Promise<Message[]> {
  return request<Message[]>(`/jarvis/conversations/${sessionId}`)
}

export function getVoiceSignedUrl(): Promise<{ signed_url: string }> {
  return request<{ signed_url: string }>('/jarvis/voice/signed-url')
}

export function executeTool(name: string, params: Record<string, unknown>): Promise<string> {
  return request<{ result: string }>(`/jarvis/tools/${name}`, {
    method: 'POST',
    body: JSON.stringify(params)
  }).then((r) => r.result)
}
