import { onMounted, onUnmounted, type ComputedRef, type Ref } from 'vue'
import {
  KEEPALIVE_MS,
  WARM_WINDOW_MS,
  ensureReachable,
  notePiReachable,
  piLastOkAt,
  piProbing,
  piStatus,
  piUnreachable,
  probeNow,
  resetPiConnectivityForTests,
  type PiReachabilityStatus,
} from '@/store/connectivity'

export {
  KEEPALIVE_MS,
  WARM_WINDOW_MS,
  ensureReachable,
  notePiReachable,
  piLastOkAt,
  piProbing,
  piStatus,
  piUnreachable,
  probeNow,
  resetPiConnectivityForTests,
}
export type { PiReachabilityStatus }

export function usePiConnectivity(): {
  status: Ref<PiReachabilityStatus>
  lastOkAt: Ref<number | null>
  probing: Ref<boolean>
  unreachable: ComputedRef<boolean>
  ensureReachable: typeof ensureReachable
  probeNow: typeof probeNow
} {
  return {
    status: piStatus,
    lastOkAt: piLastOkAt,
    probing: piProbing,
    unreachable: piUnreachable,
    ensureReachable,
    probeNow,
  }
}

/** Resume + 30s keepalive while visible. Mount once from the app shell. */
export function usePiConnectivityKeepalive(): void {
  let timer: ReturnType<typeof setInterval> | null = null

  function tick(): void {
    if (document.visibilityState !== 'visible') return
    void probeNow()
  }

  function startTimer(): void {
    if (timer) return
    timer = setInterval(tick, KEEPALIVE_MS)
  }

  function stopTimer(): void {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  function onVisible(): void {
    if (document.visibilityState === 'visible') {
      tick()
      startTimer()
    } else {
      stopTimer()
    }
  }

  onMounted(() => {
    document.addEventListener('visibilitychange', onVisible)
    if (document.visibilityState === 'visible') {
      tick()
      startTimer()
    }
  })

  onUnmounted(() => {
    stopTimer()
    document.removeEventListener('visibilitychange', onVisible)
  })
}
