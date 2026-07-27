export type TapToPayAdminStatusCode =
  | 'checking'
  | 'ready'
  | 'ready_simulated'
  | 'location_missing'
  | 'unsupported'
  | 'error'
  | 'unavailable'

export type TapToPayEligibilityCheck = {
  id: string
  ok: boolean
  detail?: string | null
}

export type TapToPayAdminStatus = {
  code: TapToPayAdminStatusCode
  detail?: string | null
  checks?: TapToPayEligibilityCheck[]
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
  checks?: unknown
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

function parseChecks(raw: unknown): TapToPayEligibilityCheck[] | undefined {
  if (!Array.isArray(raw)) return undefined
  const checks: TapToPayEligibilityCheck[] = []
  for (const entry of raw) {
    if (!entry || typeof entry !== 'object') continue
    const row = entry as Record<string, unknown>
    if (typeof row.id !== 'string' || typeof row.ok !== 'boolean') continue
    checks.push({
      id: row.id,
      ok: row.ok,
      ...(row.detail != null ? { detail: String(row.detail) } : {}),
    })
  }
  return checks
}

function mapPayload(payload: SupportPayload): TapToPayAdminStatus {
  const code = payload.code != null ? String(payload.code) : null
  const error = payload.error != null ? String(payload.error) : null
  const checks = parseChecks(payload.checks)

  let status: TapToPayAdminStatus
  if (code === 'ready_simulated' || (payload.supported === true && payload.simulated === true)) {
    status = { code: 'ready_simulated' }
  } else if (code === 'ready' || payload.supported === true) {
    status = { code: 'ready' }
  } else if (
    code === 'location_missing' ||
    (payload.ok === false && error?.includes(LOCATION_ERROR_SNIPPET))
  ) {
    status = { code: 'location_missing' }
  } else if (code === 'unsupported' || payload.supported === false) {
    status = { code: 'unsupported', detail: error }
  } else if (code === 'error' || payload.ok === false) {
    status = { code: 'error', detail: error }
  } else {
    status = { code: 'unavailable' }
  }

  if (checks && checks.length > 0) {
    status = { ...status, checks }
  }
  return status
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

const CHECK_LABELS: Record<string, string> = {
  location: 'Standortberechtigung',
  android_version: 'Android 13+',
  nfc: 'NFC',
  hardware_keystore: 'Hardware-Keystore',
  gms: 'Google Play / GMS',
  security_patch: 'Sicherheitsupdate',
  developer_options: 'Entwickleroptionen aus',
  internet: 'Internetverbindung',
  sdk_support: 'Stripe SDK',
}

/** German Admin label (Pi Admin has no i18n; matches hardcoded AdminHub strings). */
export function tapToPayAdminStatusLabel(status: TapToPayAdminStatus): string {
  return LABELS[status.code] ?? LABELS.unavailable
}

export function tapToPayEligibilityCheckLabel(id: string): string {
  return CHECK_LABELS[id] ?? id
}

/** Show the full checklist only when the bridge returned checks and at least one failed. */
export function shouldShowTapToPayEligibilityChecks(status: TapToPayAdminStatus): boolean {
  const checks = status.checks
  if (!checks || checks.length === 0) return false
  return checks.some((c) => !c.ok)
}
