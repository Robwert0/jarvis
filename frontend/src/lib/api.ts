// Typed client for the Jarvis FastAPI backend (/jarvis/*).
//
// Dev: VITE_API_BASE unset -> relative URLs, proxied by Vite to :8000.
// Packaged Tauri build: set VITE_API_BASE=http://127.0.0.1:8000 so the
// webview talks to the local backend directly (backend has CORS enabled).

const BASE = import.meta.env.VITE_API_BASE ?? "";

export interface ActionView {
  tool: string;
  summary: string;
}

export interface ChatResponse {
  reply: string;
  session_id: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  actions: ActionView[];
}

export interface ConversationSummary {
  id: string;
  title: string;
  updated_at: string;
}

export interface Message {
  role: "user" | "assistant" | string;
  content: string;
}

export interface MemoryView {
  id: number;
  content: string;
  created_at: string;
}

export type MacroAppEntry = string | { app: string; args: string[] };

export interface MacroView {
  name: string;
  apps: MacroAppEntry[];
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  // 204 No Content
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  health: () => req<{ status: string }>("/jarvis/healthz"),

  chat: (message: string, sessionId: string | null) =>
    req<ChatResponse>("/jarvis/chat", {
      method: "POST",
      body: JSON.stringify({ message, session_id: sessionId }),
    }),

  listConversations: () =>
    req<ConversationSummary[]>("/jarvis/conversations"),

  getConversation: (id: string) =>
    req<Message[]>(`/jarvis/conversations/${encodeURIComponent(id)}`),

  deleteConversation: (id: string) =>
    req<void>(`/jarvis/conversations/${encodeURIComponent(id)}`, {
      method: "DELETE",
    }),

  listMemories: () => req<MemoryView[]>("/jarvis/memories"),

  deleteMemory: (id: number) =>
    req<void>(`/jarvis/memories/${id}`, { method: "DELETE" }),

  listMacros: () => req<MacroView[]>("/jarvis/macros"),

  createMacro: (name: string, apps: MacroAppEntry[]) =>
    req<MacroView>("/jarvis/macros", {
      method: "POST",
      body: JSON.stringify({ name, apps }),
    }),

  upsertMacro: (name: string, apps: MacroAppEntry[]) =>
    req<MacroView>(`/jarvis/macros/${encodeURIComponent(name)}`, {
      method: "PUT",
      body: JSON.stringify({ apps }),
    }),

  deleteMacro: (name: string) =>
    req<void>(`/jarvis/macros/${encodeURIComponent(name)}`, {
      method: "DELETE",
    }),
};
