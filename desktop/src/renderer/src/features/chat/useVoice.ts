import { useRef, useState } from 'react'
import { Conversation } from '@elevenlabs/client'
import { executeTool, getMemories, getVoiceSignedUrl } from '../../shared/api'

export type VoiceStatus = 'idle' | 'connecting' | 'listening' | 'speaking'

const TOOL_NAMES = [
  'open_app',
  'run_macro',
  'cancel_action',
  'remember',
  'search_web',
  'control_system'
] as const

const clientTools = Object.fromEntries(
  TOOL_NAMES.map((name) => [
    name,
    (params: Record<string, unknown>): Promise<string> => executeTool(name, params)
  ])
)

interface UseVoiceOptions {
  onMessage: (role: 'user' | 'assistant', content: string) => void
  onError: (message: string) => void
}

export function useVoice({ onMessage, onError }: UseVoiceOptions): {
  status: VoiceStatus
  toggle: () => Promise<void>
} {
  const [status, setStatus] = useState<VoiceStatus>('idle')
  const sessionRef = useRef<Conversation | null>(null)

  async function toggle(): Promise<void> {
    if (sessionRef.current) {
      await sessionRef.current.endSession()
      sessionRef.current = null
      setStatus('idle')
      return
    }
    setStatus('connecting')
    try {
      const [{ signed_url }, memories] = await Promise.all([
        getVoiceSignedUrl(),
        getMemories().catch(() => [])
      ])
      sessionRef.current = await Conversation.startSession({
        signedUrl: signed_url,
        clientTools,
        onMessage: ({ message, source }) => {
          onMessage(source === 'ai' ? 'assistant' : 'user', message)
        },
        onModeChange: ({ mode }) => {
          setStatus(mode === 'speaking' ? 'speaking' : 'listening')
        },
        onDisconnect: () => {
          sessionRef.current = null
          setStatus('idle')
        },
        onError: (message) => {
          onError(String(message))
        }
      })
      if (memories.length) {
        sessionRef.current.sendContextualUpdate(
          "Here's what you should remember about the user:\n" +
            memories.map((m) => `- ${m.content}`).join('\n')
        )
      }
      setStatus('listening')
    } catch (err) {
      sessionRef.current = null
      setStatus('idle')
      onError(String(err))
    }
  }

  return { status, toggle }
}
