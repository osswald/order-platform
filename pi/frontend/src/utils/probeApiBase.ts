import { getApiBase } from '@/api/base'

export const PLAY_REVIEW_DEMO_API_BASE = 'https://play-review.demo.vendiqo.ch'

/** Client-side bound so unreachable LAN IPs do not wait for OS TCP timeouts. */
export const PROBE_TIMEOUT_MS = 2500

export type ProbeResult =
  | { reachable: true }
  | { reachable: false; reason: 'network' | 'http'; message?: string }

function normalizeBase(url: string): string {
  return url.trim().replace(/\/$/, '')
}

/** AbortSignal.timeout is missing on some Android System WebViews. */
function timeoutSignal(ms: number): { signal: AbortSignal; cancel: () => void } {
  if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') {
    return { signal: AbortSignal.timeout(ms), cancel: () => {} }
  }
  const controller = new AbortController()
  const timer = setTimeout(() => {
    controller.abort(new DOMException('Signal timed out', 'TimeoutError'))
  }, ms)
  return {
    signal: controller.signal,
    cancel: () => clearTimeout(timer),
  }
}

export async function probeApiBase(base?: string): Promise<ProbeResult> {
  const apiBase = normalizeBase(base ?? getApiBase())
  const { signal, cancel } = timeoutSignal(PROBE_TIMEOUT_MS)
  try {
    const res = await fetch(`${apiBase}/health`, {
      method: 'GET',
      signal,
    })
    if (res.ok) return { reachable: true }
    return { reachable: false, reason: 'http', message: `HTTP ${res.status}` }
  } catch {
    return { reachable: false, reason: 'network' }
  } finally {
    cancel()
  }
}
