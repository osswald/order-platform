import { getApiBase } from '@/api/base'

export const PLAY_REVIEW_DEMO_API_BASE = 'https://play-review.demo.vendiqo.ch'

export type ProbeResult =
  | { reachable: true }
  | { reachable: false; reason: 'network' | 'http'; message?: string }

function normalizeBase(url: string): string {
  return url.trim().replace(/\/$/, '')
}

export async function probeApiBase(base?: string): Promise<ProbeResult> {
  const apiBase = normalizeBase(base ?? getApiBase())
  try {
    const res = await fetch(`${apiBase}/health`, { method: 'GET' })
    if (res.ok) return { reachable: true }
    return { reachable: false, reason: 'http', message: `HTTP ${res.status}` }
  } catch {
    return { reachable: false, reason: 'network' }
  }
}
