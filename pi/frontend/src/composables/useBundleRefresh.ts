import { onMounted, onUnmounted } from 'vue'
import { bundleReady, refreshBundle } from '@/store'

const REFRESH_MS = 60_000

/** Reload bundle from local Pi API while the tab is visible (matches backend sync interval). */
export function useBundleRefresh(): void {
  let timer: ReturnType<typeof setInterval> | null = null

  function tick(): void {
    if (document.visibilityState !== 'visible') return
    refreshBundle().catch(() => {})
  }

  function startTimer(): void {
    if (timer) return
    timer = setInterval(tick, REFRESH_MS)
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
    if (bundleReady()) tick()
    document.addEventListener('visibilitychange', onVisible)
    if (document.visibilityState === 'visible') startTimer()
  })

  onUnmounted(() => {
    stopTimer()
    document.removeEventListener('visibilitychange', onVisible)
  })
}
