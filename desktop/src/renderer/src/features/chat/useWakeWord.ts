import { useEffect, useRef } from 'react'
import { BuiltInKeyword, PorcupineWorker } from '@picovoice/porcupine-web'
import { WebVoiceProcessor } from '@picovoice/web-voice-processor'
import { getWakeConfig } from '../../shared/api'

interface UseWakeWordOptions {
  enabled: boolean
  suspended: boolean
  onWake: () => void
  onError: (message: string) => void
}

export function useWakeWord({ enabled, suspended, onWake, onError }: UseWakeWordOptions): void {
  const workerRef = useRef<PorcupineWorker | null>(null)
  const suspendedRef = useRef(suspended)
  const onWakeRef = useRef(onWake)
  const onErrorRef = useRef(onError)

  useEffect(() => {
    onWakeRef.current = onWake
    onErrorRef.current = onError
  })

  useEffect(() => {
    if (!enabled) return
    let cancelled = false

    async function start(): Promise<void> {
      try {
        const { access_key } = await getWakeConfig()
        const worker = await PorcupineWorker.create(
          access_key,
          BuiltInKeyword.Jarvis,
          () => onWakeRef.current(),
          { publicPath: 'porcupine_params.pv' }
        )
        if (cancelled) {
          worker.release()
          worker.terminate()
          return
        }
        workerRef.current = worker
        if (!suspendedRef.current) await WebVoiceProcessor.subscribe(worker)
      } catch (err) {
        onErrorRef.current(String(err))
      }
    }
    start()

    return () => {
      cancelled = true
      const worker = workerRef.current
      workerRef.current = null
      if (worker) {
        WebVoiceProcessor.unsubscribe(worker).catch(() => {})
        worker.release()
        worker.terminate()
      }
    }
  }, [enabled])

  useEffect(() => {
    suspendedRef.current = suspended
    const worker = workerRef.current
    if (!worker) return
    const action = suspended
      ? WebVoiceProcessor.unsubscribe(worker)
      : WebVoiceProcessor.subscribe(worker)
    action.catch((err) => onErrorRef.current(String(err)))
  }, [suspended])
}
