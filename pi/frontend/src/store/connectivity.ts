import { computed, ref } from 'vue'
import { probeApiBase, type ProbeResult } from '@/utils/probeApiBase'

/** Skip force-probe on gated CTAs when last success was this recent. */
export const WARM_WINDOW_MS = 20_000

/** Mid-session /health keepalive while the document is visible. */
export const KEEPALIVE_MS = 30_000

export type PiReachabilityStatus = 'unknown' | 'reachable' | 'unreachable'

export const piStatus = ref<PiReachabilityStatus>('unknown')
export const piLastOkAt = ref<number | null>(null)
export const piProbing = ref(false)

export const piUnreachable = computed(() => piStatus.value === 'unreachable')

let inflight: Promise<boolean> | null = null

function applyResult(result: ProbeResult): boolean {
  if (result.reachable) {
    piStatus.value = 'reachable'
    piLastOkAt.value = Date.now()
    return true
  }
  piStatus.value = 'unreachable'
  return false
}

/** Seed mid-session state after a successful cold-start probe (no extra network call). */
export function notePiReachable(): void {
  piStatus.value = 'reachable'
  piLastOkAt.value = Date.now()
}

export async function probeNow(): Promise<boolean> {
  if (inflight) return inflight
  piProbing.value = true
  inflight = (async () => {
    try {
      const result = await probeApiBase()
      return applyResult(result)
    } catch {
      piStatus.value = 'unreachable'
      return false
    } finally {
      piProbing.value = false
      inflight = null
    }
  })()
  return inflight
}

export async function ensureReachable(opts?: { force?: boolean }): Promise<boolean> {
  if (
    !opts?.force &&
    piStatus.value === 'reachable' &&
    piLastOkAt.value != null &&
    Date.now() - piLastOkAt.value <= WARM_WINDOW_MS
  ) {
    return true
  }
  return probeNow()
}

export function resetPiConnectivityForTests(): void {
  piStatus.value = 'unknown'
  piLastOkAt.value = null
  piProbing.value = false
  inflight = null
}
