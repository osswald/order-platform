export type TapToPayAdminStatusCode =
  | 'checking'
  | 'ready'
  | 'ready_simulated'
  | 'location_missing'
  | 'unsupported'
  | 'error'
  | 'unavailable'

export type TapToPayAdminStatus = {
  code: TapToPayAdminStatusCode
  detail?: string | null
}

const LOCATION_ERROR_SNIPPET = 'Standortberechtigung'

let adminCache: TapToPayAdminStatus | null = null

/** Test helper. */
export function resetTapToPayAdminStatusCacheForTests(): void {
  adminCache = null
}

function bridge(): Record<string, (...args: unknown[]) => unknown> | null {
  if (typeof window === 'undefined') return null
  return window.AndroidTerminal || null
}

type SupportPayload = {
  ok?: boolean
  supported?: boolean
  code?: string
  simulated?: boolean
  error?: string
}

function parsePayload(raw: unknown): SupportPayload {
  if (!raw) return { ok: false, error: 'Keine Antwort vom Android-Terminal.' }
  if (typeof raw === 'object') return raw as SupportPayload
  try {
    return JSON.parse(String(raw)) as SupportPayload
  } catch {
    return { ok: false, error: String(raw) }
  }
}

function mapPayload(payload: SupportPayload): TapToPayAdminStatus {
  const code = payload.code != null ? String(payload.code) : null
  const error = payload.error != null ? String(payload.error) : null

  if (code === 'ready_simulated' || (payload.supported === true && payload.simulated === true)) {
    return { code: 'ready_simulated' }
  }
  if (code === 'ready' || payload.supported === true) {
    return { code: 'ready' }
  }
  if (code === 'location_missing' || (payload.ok === false && error?.includes(LOCATION_ERROR_SNIPPET))) {
    return { code: 'location_missing' }
  }
  if (code === 'unsupported' || payload.supported === false) {
    return { code: 'unsupported', detail: error }
  }
  if (code === 'error' || payload.ok === false) {
    return { code: 'error', detail: error }
  }
  return { code: 'unavailable' }
}

/**
 * Admin Tap to Pay readiness for the current device.
 * Uses `AndroidTerminal.supportsTapToPay` (non-charging). Prefer `force=true` on Admin open.
 */
export function checkTapToPayAdminStatus(force = false): TapToPayAdminStatus {
  if (!force && adminCache) return adminCache

  const b = bridge()
  if (!b || typeof b.supportsTapToPay !== 'function') {
    adminCache = { code: 'unavailable' }
    return adminCache
  }

  try {
    const payload = parsePayload(b.supportsTapToPay())
    adminCache = mapPayload(payload)
  } catch (e: unknown) {
    const detail = e instanceof Error ? e.message : 'Android-Terminalfehler.'
    adminCache = { code: 'error', detail }
  }
  return adminCache
}

const LABELS: Record<TapToPayAdminStatusCode, string> = {
  checking: 'prüfen…',
  ready: 'bereit',
  ready_simulated: 'bereit (simuliert)',
  location_missing: 'Standort fehlt',
  unsupported: 'nicht unterstützt',
  error: 'Fehler',
  unavailable: 'nicht verfügbar',
}

/** German Admin label (Pi Admin has no i18n; matches hardcoded AdminHub strings). */
export function tapToPayAdminStatusLabel(status: TapToPayAdminStatus): string {
  return LABELS[status.code] ?? LABELS.unavailable
}
