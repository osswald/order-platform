import { api } from '@/api'

interface BridgeResult extends AndroidBridgeResult {
  printers?: unknown[]
  address?: string
  escpos_payload?: string
  payment_intent_id?: string
}

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
