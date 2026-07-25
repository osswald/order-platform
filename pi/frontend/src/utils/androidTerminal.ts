import { api } from '@/api'

interface BridgeResult extends AndroidBridgeResult {
  printers?: unknown[]
  address?: string
  escpos_payload?: string
  payment_intent_id?: string
  supported?: boolean
}

export type TapToPaySupportStatus =
  | { status: 'unknown' }
  | { status: 'supported' }
  | { status: 'unsupported'; error?: string | null }
  | { status: 'check_failed'; error: string }

let supportCache: TapToPaySupportStatus | null = null

function bridge(): Record<string, (...args: unknown[]) => unknown> | null {
  if (typeof window === 'undefined') return null
  return window.AndroidTerminal || null
}

function parseResult(raw: unknown): BridgeResult {
  if (!raw) return { ok: false, error: 'Keine Antwort vom Android-Terminal.' }
  if (typeof raw === 'object') return raw as BridgeResult
  try {
    return JSON.parse(String(raw)) as BridgeResult
  } catch {
    return { ok: false, error: String(raw) }
  }
}

function call(method: string, ...args: unknown[]): BridgeResult {
  const b = bridge()
  if (!b || typeof b[method] !== 'function') {
    return { ok: false, error: 'Android-Terminal ist nicht verfügbar.' }
  }
  try {
    return parseResult(b[method](...args))
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : 'Android-Terminalfehler.'
    return { ok: false, error: message }
  }
}

export function isAndroidTerminalAvailable(): boolean {
  return Boolean(bridge())
}

/** Test helper — clears the session cache for Tap to Pay device support. */
export function resetTapToPaySupportCacheForTests(): void {
  supportCache = null
}

/**
 * Query native Tap to Pay device support via `AndroidTerminal.supportsTapToPay`.
 * Missing bridge method (older APK) → `{ status: 'unknown' }` (fail open for the picker).
 */
export function checkTapToPayDeviceSupport(force = false): TapToPaySupportStatus {
  if (!force && supportCache) return supportCache

  const b = bridge()
  if (!b || typeof b.supportsTapToPay !== 'function') {
    const unknown: TapToPaySupportStatus = { status: 'unknown' }
    supportCache = unknown
    return unknown
  }

  const result = call('supportsTapToPay')
  let status: TapToPaySupportStatus
  if (result.ok === false) {
    status = {
      status: 'check_failed',
      error: String(result.error || 'Tap-to-Pay-Unterstützung konnte nicht geprüft werden.'),
    }
  } else if (result.supported === true) {
    status = { status: 'supported' }
  } else if (result.supported === false) {
    status = {
      status: 'unsupported',
      error: result.error != null ? String(result.error) : null,
    }
  } else {
    status = {
      status: 'check_failed',
      error: String(result.error || 'Tap-to-Pay-Unterstützung konnte nicht geprüft werden.'),
    }
  }
  supportCache = status
  return status
}

export interface CreateTerminalPaymentIntentInput {
  eventId: number
  amountCents: number
  currency: string
  clientOrderId?: string | null
  metadata?: Record<string, string>
}

export async function createTerminalPaymentIntent({
  eventId,
  amountCents,
  currency,
  clientOrderId,
  metadata = {},
}: CreateTerminalPaymentIntentInput): Promise<{ id: string; client_secret: string }> {
  return api('/v1/terminal/payment-intents', {
    method: 'POST',
    body: JSON.stringify({
      event_id: eventId,
      amount_cents: amountCents,
      currency,
      client_order_id: clientOrderId,
      idempotency_key: clientOrderId ? `terminal-${clientOrderId}` : undefined,
      metadata,
    }),
  })
}

export interface CollectTerminalPaymentInput {
  eventId: number
  amountCents: number
  currency: string
  clientOrderId?: string | null
  metadata?: Record<string, string>
}

export async function collectTerminalPayment({
  eventId,
  amountCents,
  currency,
  clientOrderId,
  metadata = {},
}: CollectTerminalPaymentInput): Promise<{
  type: 'stripe_terminal'
  amount_cents: number
  stripe_payment_intent_id: string
}> {
  const intent = await createTerminalPaymentIntent({ eventId, amountCents, currency, clientOrderId, metadata })
  const token = await api<{ secret: string }>('/v1/terminal/connection-token', {
    method: 'POST',
    body: JSON.stringify({ event_id: eventId }),
  })
  const result = call('collectPayment', token.secret, intent.client_secret)
  if (!result.ok) throw new Error(result.error || 'Kartenzahlung fehlgeschlagen.')
  return {
    type: 'stripe_terminal',
    amount_cents: amountCents,
    stripe_payment_intent_id: String(result.payment_intent_id || intent.id),
  }
}
