import { onMounted, onUnmounted, ref } from 'vue'

/**
 * Soft-keyboard coverage at the bottom of the layout viewport (CSS px),
 * derived from `visualViewport`. Returns 0 when the API is missing or the
 * keyboard is not covering the bottom.
 *
 * Use only on sheets/dialogs that contain text inputs.
 */
export function useKeyboardBottomInset() {
  const keyboardBottomInset = ref(0)

  function update() {
    if (typeof window === 'undefined') {
      keyboardBottomInset.value = 0
      return
    }
    const vv = window.visualViewport
    if (!vv) {
      keyboardBottomInset.value = 0
      return
    }
    const inset = Math.max(0, Math.round(window.innerHeight - vv.height - vv.offsetTop))
    keyboardBottomInset.value = inset
  }

  onMounted(() => {
    update()
    const vv = window.visualViewport
    vv?.addEventListener('resize', update)
    vv?.addEventListener('scroll', update)
    window.addEventListener('resize', update)
  })

  onUnmounted(() => {
    const vv = window.visualViewport
    vv?.removeEventListener('resize', update)
    vv?.removeEventListener('scroll', update)
    window.removeEventListener('resize', update)
  })

  return keyboardBottomInset
}
