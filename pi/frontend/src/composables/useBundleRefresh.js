import { onMounted, onUnmounted } from 'vue'
import * as store from '../store'

const REFRESH_MS = 60_000

/** Reload bundle from local Pi API while the tab is visible (matches backend sync interval). */
export function useBundleRefresh() {
  let timer = null

  function tick() {
    if (document.visibilityState !== 'visible') return
    store.refreshBundle().catch(() => {})
  }

  function startTimer() {
    if (timer) return
    timer = setInterval(tick, REFRESH_MS)
  }

  function stopTimer() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  function onVisible() {
    if (document.visibilityState === 'visible') {
      tick()
      startTimer()
    } else {
      stopTimer()
    }
  }

  onMounted(() => {
    if (store.bundleReady()) tick()
    document.addEventListener('visibilitychange', onVisible)
    if (document.visibilityState === 'visible') startTimer()
  })

  onUnmounted(() => {
    stopTimer()
    document.removeEventListener('visibilitychange', onVisible)
  })
}
