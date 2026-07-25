import { onMounted, onUnmounted, ref } from 'vue'
import {
  ANDROID_INSETS_EVENT,
  readAndroidImeBottomInset,
  readAndroidSafeBottomInset,
} from '@/utils/androidInsets'

/**
 * Soft-keyboard coverage at the bottom of the layout viewport (CSS px).
 *
 * On Android edge-to-edge WebView, `visualViewport` often does not shrink when
 * the IME opens. Prefer the native `--ime-bottom` / AndroidInsets bridge, and
 * fall back to `visualViewport`. The returned value is the *extra* padding
 * beyond `--safe-bottom` so sheets can use:
 * `padding-bottom: calc(1rem + var(--safe-bottom) + var(--keyboard-bottom))`.
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

    const imeBottom = readAndroidImeBottomInset()
    const safeBottom = readAndroidSafeBottomInset()
    // IME already covers the nav-bar region; only add the delta beyond safe-bottom.
    const androidExtra = Math.max(0, imeBottom - safeBottom)

    let vvExtra = 0
    const vv = window.visualViewport
    if (vv) {
      const covered = Math.max(0, Math.round(window.innerHeight - vv.height - vv.offsetTop))
      vvExtra = Math.max(0, covered - safeBottom)
    }

    keyboardBottomInset.value = Math.max(androidExtra, vvExtra)
  }

  onMounted(() => {
    update()
    const vv = window.visualViewport
    vv?.addEventListener('resize', update)
    vv?.addEventListener('scroll', update)
    window.addEventListener('resize', update)
    window.addEventListener(ANDROID_INSETS_EVENT, update)
  })

  onUnmounted(() => {
    const vv = window.visualViewport
    vv?.removeEventListener('resize', update)
    vv?.removeEventListener('scroll', update)
    window.removeEventListener('resize', update)
    window.removeEventListener(ANDROID_INSETS_EVENT, update)
  })

  return keyboardBottomInset
}
