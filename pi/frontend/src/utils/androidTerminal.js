import { api } from '../api'

function bridge() {
  if (typeof window === 'undefined') return null
  return window.AndroidTerminal || null
}

function parseResult(raw) {
  if (!raw) return { ok: false, error: 'Keine Antwort vom Android-Terminal.' }
  if (typeof raw === 'object') return raw
  try {
    return JSON.parse(raw)
  } catch {
    return { ok: false, error: String(raw) }
  }
}

function call(method, ...args) {
  const b = bridge()
  if (!b || typeof b[method] !== 'function') {
    return { ok: false, error: 'Android-Terminal ist nicht verfügbar.' }
  }
  try {
    return parseResult(b[method](...args))
  } catch (e) {
    return { ok: false, error: e?.message || 'Android-Terminalfehler.' }
  }
}

export function isAndroidTerminalAvailable() {
  return Boolean(bridge())
}

export async function createTerminalPaymentIntent({ eventId, amountCents, currency, clientOrderId, metadata = {} }) {
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

export async function collectTerminalPayment({ eventId, amountCents, currency, clientOrderId, metadata = {} }) {
  const intent = await createTerminalPaymentIntent({ eventId, amountCents, currency, clientOrderId, metadata })
  const token = await api('/v1/terminal/connection-token', {
    method: 'POST',
    body: JSON.stringify({ event_id: eventId }),
  })
  const result = call('collectPayment', token.secret, intent.client_secret)
  if (!result.ok) throw new Error(result.error || 'Kartenzahlung fehlgeschlagen.')
  return {
    type: 'stripe_terminal',
    amount_cents: amountCents,
    stripe_payment_intent_id: result.payment_intent_id || intent.id,
  }
}
