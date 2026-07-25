interface AppInfoBridgeResult extends AndroidBridgeResult {
  versionName?: string
  versionCode?: number | string
}

export type AndroidAppInfo =
  | { status: 'unavailable' }
  | { status: 'ok'; versionName: string; versionCode: number | null }

function bridge(): { getAppInfo?: () => unknown } | null {
  if (typeof window === 'undefined') return null
  return window.AndroidApp || null
}

function parseResult(raw: unknown): AppInfoBridgeResult {
  if (!raw) return { ok: false, error: 'Keine Antwort von AndroidApp.' }
  if (typeof raw === 'object') return raw as AppInfoBridgeResult
  try {
    return JSON.parse(String(raw)) as AppInfoBridgeResult
  } catch {
    return { ok: false, error: String(raw) }
  }
}

/**
 * Read native APK version via `window.AndroidApp.getAppInfo()`.
 * Missing bridge (browser / older APK) → `{ status: 'unavailable' }`.
 */
export function getAndroidAppInfo(): AndroidAppInfo {
  const b = bridge()
  if (!b || typeof b.getAppInfo !== 'function') {
    return { status: 'unavailable' }
  }
  try {
    const result = parseResult(b.getAppInfo())
    const versionName = result.versionName != null ? String(result.versionName).trim() : ''
    if (result.ok === false || !versionName) {
      return { status: 'unavailable' }
    }
    const codeRaw = result.versionCode
    let versionCode: number | null = null
    if (typeof codeRaw === 'number' && Number.isFinite(codeRaw)) {
      versionCode = codeRaw
    } else if (typeof codeRaw === 'string') {
      const trimmed = codeRaw.trim()
      if (trimmed !== '' && Number.isFinite(Number(trimmed))) {
        versionCode = Number(trimmed)
      }
    }
    return { status: 'ok', versionName, versionCode }
  } catch {
    return { status: 'unavailable' }
  }
}
