import type { MemoryView } from './types'

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
