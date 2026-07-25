/** Custom event name fired after Android inset CSS variables are updated. */
export const ANDROID_INSETS_EVENT = 'vendiqo-android-insets'

/** Apply system bar + IME insets from AndroidInsets bridge (see AndroidInsetsBridge.kt). */
export function applyAndroidSafeAreaInsets() {
  if (typeof window === 'undefined') return
  const bridge = window.AndroidInsets
  if (!bridge?.getSystemBarInsetsJson) return
  try {
    const o = JSON.parse(bridge.getSystemBarInsetsJson())
    const root = document.documentElement
    root.style.setProperty('--safe-top', `${Number(o.top) || 0}px`)
    root.style.setProperty('--safe-bottom', `${Number(o.bottom) || 0}px`)
    root.style.setProperty('--safe-left', `${Number(o.left) || 0}px`)
    root.style.setProperty('--safe-right', `${Number(o.right) || 0}px`)
    let imeBottom = 0
    if (bridge.getImeInsetsJson) {
      try {
        const ime = JSON.parse(bridge.getImeInsetsJson())
        imeBottom = Number(ime.bottom) || 0
      } catch {
        imeBottom = 0
      }
    }
    root.style.setProperty('--ime-bottom', `${imeBottom}px`)
    window.dispatchEvent(new Event(ANDROID_INSETS_EVENT))
  } catch {
    /* ignore */
  }
}

/**
 * Soft-keyboard coverage from the Android IME inset bridge (CSS px).
 * 0 when not in the Android app or keyboard is closed.
 */
export function readAndroidImeBottomInset(): number {
  if (typeof window === 'undefined') return 0
  const bridge = window.AndroidInsets
  if (bridge?.getImeInsetsJson) {
    try {
      const o = JSON.parse(bridge.getImeInsetsJson())
      return Math.max(0, Number(o.bottom) || 0)
    } catch {
      /* fall through */
    }
  }
  if (typeof document === 'undefined') return 0
  const raw = getComputedStyle(document.documentElement).getPropertyValue('--ime-bottom')
  const n = parseFloat(raw)
  return Number.isFinite(n) ? Math.max(0, n) : 0
}

/** System-bar bottom inset currently applied as --safe-bottom (CSS px). */
export function readAndroidSafeBottomInset(): number {
  if (typeof document === 'undefined') return 0
  const raw = getComputedStyle(document.documentElement).getPropertyValue('--safe-bottom')
  const n = parseFloat(raw)
  return Number.isFinite(n) ? Math.max(0, n) : 0
}
