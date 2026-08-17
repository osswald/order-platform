import type { EdgeBundleEvent, PaymentIn } from '@/types/api'

export const PAYMENT_TYPE_ORDER = ['cash', 'twint', 'sumup', 'sumup_connected'] as const

export type PaymentType = (typeof PAYMENT_TYPE_ORDER)[number]

export const PAYMENT_TYPE_LABELS: Record<PaymentType, string> = {
  cash: 'Bargeld',
  twint: 'TWINT',
  sumup: 'Sumup (manual)',
  sumup_connected: 'Sumup connected',
}

/** Labels for historical / legacy payment rows still present in synced orders. */
const LEGACY_PAYMENT_TYPE_LABELS: Record<string, string> = {
  stripe_terminal: 'Karte',
}

export function paymentTypeLabel(type: string | null | undefined): string {
  const key = String(type || '').toLowerCase()
  if (key in PAYMENT_TYPE_LABELS) return PAYMENT_TYPE_LABELS[key as PaymentType]
  if (key in LEGACY_PAYMENT_TYPE_LABELS) return LEGACY_PAYMENT_TYPE_LABELS[key]
  return key || '—'
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

export interface SumupReceiptInfo {
  transaction_code?: string | null
  auth_code?: string | null
  card_last_4?: string | null
  card_type?: string | null
  entry_mode?: string | null
  timestamp?: string | null
  merchant_code?: string | null
}

export function sanitizeSumupReceiptInfo(
  info: SumupReceiptInfo | null | undefined,
): Record<string, string> | undefined {
  if (!info || typeof info !== 'object') return undefined
  const out: Record<string, string> = {}
  for (const [key, value] of Object.entries(info)) {
    if (value == null) continue
    const text = String(value).trim()
    if (text) out[key] = text
  }
  return Object.keys(out).length ? out : undefined
}

export function buildSumupConnectedPayment(
  amountCents: number,
  sumupTransactionId: string,
  receiptInfo?: SumupReceiptInfo | null,
): PaymentIn[] {
  const payment: PaymentIn = {
    type: 'sumup_connected',
    amount_cents: Math.max(0, Number(amountCents) || 0),
    sumup_transaction_id: String(sumupTransactionId || '').trim(),
  }
  const cleaned = sanitizeSumupReceiptInfo(receiptInfo)
  if (cleaned) {
    ;(payment as PaymentIn & { sumup_receipt_info: Record<string, string> }).sumup_receipt_info =
      cleaned
  }
  return [payment]
}
