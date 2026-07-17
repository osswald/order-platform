import type { OrderLineIn } from '@/types/api'
import type { CartLine } from '@/types/cart'

/** Client order id in the PWA format expected by the pi backend. */
export function newClientOrderId(): string {
  return `pwa-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

/** Map cart lines (incl. voucher sales) to POST /v1/orders line payloads. */
export function buildOrderPayloadLines(
  lines: CartLine[],
  opts: { positionCommentsEnabled: boolean; discountsEnabled: boolean },
): OrderLineIn[] {
  return lines.map((l) => {
    if (l.kind === 'voucher_sale') {
      return {
        kind: 'voucher_sale',
        voucher_definition_uuid: l.voucher_definition_uuid,
        qty: l.qty,
        unit_cents: l.unit_cents,
        note: '',
        additions: [],
      }
    }
    const row: OrderLineIn = {
      article_id: l.article_id,
      qty: l.qty,
      station_uuid: l.station_uuid,
      note: opts.positionCommentsEnabled ? String(l.note || '').trim() : '',
      additions: (l.additions || []).map((a) => ({ article_id: a.article_id, qty: a.qty ?? 1 })),
    }
    if (opts.discountsEnabled && l.discount) row.discount = l.discount
    return row
  })
}

/** Article lines for the stock pre-check (voucher sales carry no stock). */
export function stockLinesFromPayloadLines(payloadLines: OrderLineIn[]) {
  return payloadLines
    .filter((l) => l.article_id != null && l.kind !== 'voucher_sale')
    .map((l) => ({
      article_id: l.article_id!,
      qty: l.qty,
      additions: (l.additions || []).map((a) => ({ article_id: a.article_id, qty: a.qty ?? 1 })),
    }))
}
