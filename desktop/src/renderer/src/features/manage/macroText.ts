import type { MacroAppEntry } from '../../shared/types'

export function parseApps(text: string): MacroAppEntry[] {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [app, ...args] = line.split(/\s+/)
      return args.length ? { app, args } : app
    })
}

export function formatApps(apps: MacroAppEntry[]): string {
  return apps
    .map((entry) => (typeof entry === 'string' ? entry : [entry.app, ...entry.args].join(' ')))
    .join('\n')
}
