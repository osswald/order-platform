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
    // abort() without reason — widest WebView compatibility
    controller.abort()
  }, ms)
  return {
    signal: controller.signal,
    cancel: () => clearTimeout(timer),
  }
}

function probeViaAndroidBridge(apiBase: string): ProbeResult | null {
  if (typeof window === 'undefined') return null
  const bridge = window.AndroidNetwork
  if (!bridge || typeof bridge.probeHealth !== 'function') return null
  try {
    const raw = bridge.probeHealth(apiBase)
    const data = typeof raw === 'string' ? JSON.parse(raw) : raw
    if (data && typeof data === 'object' && (data as { ok?: unknown }).ok === true) {
      return { reachable: true }
    }
    const reason = (data as { reason?: unknown })?.reason
    const message = (data as { message?: unknown })?.message
    return {
      reachable: false,
      reason: reason === 'http' ? 'http' : 'network',
      message: typeof message === 'string' ? message : undefined,
    }
  } catch {
    // Fall through to fetch (bridge unavailable / malformed payload).
    return null
  }
}

export async function probeApiBase(base?: string): Promise<ProbeResult> {
  const apiBase = normalizeBase(base ?? getApiBase())
  const fromBridge = probeViaAndroidBridge(apiBase)
  if (fromBridge) return fromBridge

  const { signal, cancel } = timeoutSignal(PROBE_TIMEOUT_MS)
  try {
    const res = await fetch(`${apiBase}/health`, {
      method: 'GET',
      signal,
      // Avoid credentialed CORS mode; Pi waiter API does not use cookies.
      credentials: 'omit',
    })
    if (res.ok) return { reachable: true }
    return { reachable: false, reason: 'http', message: `HTTP ${res.status}` }
  } catch {
    return { reachable: false, reason: 'network' }
  } finally {
    cancel()
  }
}
