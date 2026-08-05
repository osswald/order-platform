import { onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { isAndroidApp } from '@/api'

/** Call native immersive toggle when available (no-op off Android / older APKs). */
export function setAndroidImmersiveMode(enabled: boolean): void {
  if (!isAndroidApp()) return
  const bridge = window.AndroidApp
  const fn = bridge?.setImmersiveMode
  if (typeof fn !== 'function') return
  try {
    fn.call(bridge, enabled)
  } catch {
    /* older WebView / bridge errors must not break navigation */
  }
}

/**
 * Sync route meta.immersive → Android system bar hide/show.
 * Call once from App.vue setup.
 */
export function useAndroidImmersiveDisplay(): void {
  if (!isAndroidApp()) return
  const route = useRoute()
  watch(
    () => Boolean(route.meta.immersive),
    (immersive) => {
      setAndroidImmersiveMode(immersive)
    },
    { immediate: true },
  )
  onUnmounted(() => {
    setAndroidImmersiveMode(false)
  })
}
