import type { EdgeBundleEvent, PaymentIn } from '@/types/api'

export const PAYMENT_TYPE_ORDER = ['cash', 'twint', 'sumup', 'stripe_terminal'] as const

export type PaymentType = (typeof PAYMENT_TYPE_ORDER)[number]

export const PAYMENT_TYPE_LABELS: Record<PaymentType, string> = {
  cash: 'Bargeld',
  twint: 'TWINT',
  sumup: 'SumUp',
  stripe_terminal: 'Karte',
}

export function paymentTypeLabel(type: string | null | undefined): string {
  const key = String(type || '').toLowerCase()
  return PAYMENT_TYPE_LABELS[key as PaymentType] || key || '—'
}

export function eventPaymentTypes(event: EdgeBundleEvent | null | undefined): PaymentType[] {
  const raw = event?.payment_types
  if (!Array.isArray(raw) || !raw.length) return ['cash']
  const out: PaymentType[] = []
  for (const t of PAYMENT_TYPE_ORDER) {
    if (raw.map((x) => String(x).toLowerCase()).includes(t)) out.push(t)
  }
  return out.length ? out : ['cash']
}

export function eventTwintQrDataUrl(event: EdgeBundleEvent | null | undefined): string | null {
  const url = event?.twint_qr_data_url
  if (typeof url !== 'string' || !url.startsWith('data:')) return null
  return url
}

export function buildPayment(amountCents: number, type: string): PaymentIn[] {
  return [{ type, amount_cents: Math.max(0, Number(amountCents) || 0) }]
}

export function buildStripeTerminalPayment(amountCents: number, paymentIntentId: string): PaymentIn[] {
  return [
    {
      type: 'stripe_terminal',
      amount_cents: Math.max(0, Number(amountCents) || 0),
      stripe_payment_intent_id: String(paymentIntentId || '').trim(),
    },
  ]
}
