export const PAYMENT_TYPE_ORDER = ['cash', 'twint', 'sumup', 'stripe_terminal']

export const PAYMENT_TYPE_LABELS = {
  cash: 'Bargeld',
  twint: 'TWINT',
  sumup: 'SumUp',
  stripe_terminal: 'Karte',
}

export function paymentTypeLabel(type) {
  const key = String(type || '').toLowerCase()
  return PAYMENT_TYPE_LABELS[key] || key || '—'
}

/** Allowed payment types for an event (from synced bundle). */
export function eventPaymentTypes(event) {
  const raw = event?.payment_types
  if (!Array.isArray(raw) || !raw.length) return ['cash']
  const out = []
  for (const t of PAYMENT_TYPE_ORDER) {
    if (raw.map((x) => String(x).toLowerCase()).includes(t)) out.push(t)
  }
  return out.length ? out : ['cash']
}

/** TWINT QR data URL from synced bundle (null if none or TWINT disabled). */
export function eventTwintQrDataUrl(event) {
  const url = event?.twint_qr_data_url
  if (typeof url !== 'string' || !url.startsWith('data:')) return null
  return url
}

export function buildPayment(amountCents, type) {
  return [{ type, amount_cents: Math.max(0, Number(amountCents) || 0) }]
}
