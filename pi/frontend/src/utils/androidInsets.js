/** Apply system bar insets from AndroidInsets bridge (see AndroidInsetsBridge.kt). */
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
  } catch {
    /* ignore */
  }
}
