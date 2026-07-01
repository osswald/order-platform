import type { DiscountIn, EdgeBundleArticle, EdgeBundleEvent } from '@/types/api'
import { lineIdentityKeyFromItem } from './bundleHelpers'

/** Swiss number format: 1'234.56 (apostrophe thousands, dot decimals). */
export const MONEY_LOCALE = 'de-CH'

const amountFormatter = new Intl.NumberFormat(MONEY_LOCALE, {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

export interface MoneyLine {
  article_id?: number
  qty?: number
  note?: string
  additions?: Array<{ article_id: number; qty?: number }>
  discount?: DiscountIn | null
  kind?: string
  voucher_definition_uuid?: string
  unit_cents?: number | null
}

/** Cents → amount string without currency symbol. */
export function formatAmount(cents: number | null | undefined): string {
  return amountFormatter.format((cents || 0) / 100)
}

export function formatMoney(cents: number | null | undefined, currency = 'CHF'): string {
  return `${currency} ${formatAmount(cents)}`
}

/** Major currency units (e.g. article.price) with ISO code prefix. */
export function formatPrice(amount: number | string | null | undefined, currency = 'CHF'): string {
  return `${currency} ${amountFormatter.format(Number(amount) || 0)}`
}

function articleEntry(
  articles: Record<string, EdgeBundleArticle> | null | undefined,
  articleId: number | string,
): EdgeBundleArticle | undefined {
  return articles?.[String(articleId)] || articles?.[Number(articleId)]
}

function additionPriceCents(
  articles: Parameters<typeof articleEntry>[0],
  baseArticle: ReturnType<typeof articleEntry>,
  additionId: number | string,
): number {
  if (baseArticle?.additions) {
    for (const add of baseArticle.additions) {
      if (Number(add.article_id) === Number(additionId)) {
        return Math.round(Number(add.price || 0) * 100)
      }
    }
  }
  const a = articleEntry(articles, additionId)
  return a ? Math.round(Number(a.price || 0) * 100) : 0
}

export function articleBaseUnitCents(
  articles: Parameters<typeof articleEntry>[0],
  articleId: number | string,
): number {
  const base = articleEntry(articles, articleId)
  return base ? Math.round(Number(base.price || 0) * 100) : 0
}

export function voucherEntitlementCreditCents(
  sel: { article_id: number; note?: string; additions?: MoneyLine['additions'] },
  articles: Parameters<typeof articleEntry>[0],
  vd: { include_additions?: boolean } | null | undefined,
  event: EdgeBundleEvent | null = null,
  lineGroups: Array<{ unit_cents?: number; unitCents?: number } & MoneyLine> | null = null,
): number {
  if (vd?.include_additions) {
    if (lineGroups?.length) {
      const key = lineIdentityKeyFromItem(sel)
      const g = lineGroups.find((x) => lineIdentityKeyFromItem({ ...x, article_id: x.article_id! }) === key)
      if (g != null && (g.unit_cents != null || g.unitCents != null)) {
        return Math.max(0, Number(g.unit_cents ?? g.unitCents) || 0)
      }
    }
    return lineUnitCents(
      {
        article_id: sel.article_id,
        note: sel.note || '',
        additions: sel.additions || [],
        qty: 1,
      },
      articles,
      event,
    )
  }
  return articleBaseUnitCents(articles, sel.article_id)
}

export function lineUnitCents(
  line: MoneyLine,
  articles: Parameters<typeof articleEntry>[0],
  event: EdgeBundleEvent | null = null,
): number {
  if (line?.kind === 'voucher_sale') {
    if (line.unit_cents != null) return Math.max(0, Number(line.unit_cents))
    const defs = event?.configuration?.voucher_definitions || []
    const vUuid = String(line.voucher_definition_uuid || '')
    const vd = defs.find((d) => String(d.uuid) === vUuid)
    return Math.max(0, Number(vd?.value_cents) || 0)
  }
  if (line?.unit_cents != null) return Math.max(0, Number(line.unit_cents))
  const base = articleEntry(articles, line.article_id!)
  let unit = base ? Math.round(Number(base.price || 0) * 100) : 0
  for (const add of line.additions || []) {
    const addQty = Math.max(1, Number(add.qty) || 1)
    unit += additionPriceCents(articles, base, add.article_id) * addQty
  }
  return Math.max(0, unit)
}

export function discountsEnabled(event: EdgeBundleEvent | null | undefined): boolean {
  return Boolean(event?.discounts_enabled)
}

export function normalizeDiscount(raw: DiscountIn | null | undefined): DiscountIn | null {
  if (!raw || typeof raw !== 'object') return null
  const kind = String(raw.kind || '').toLowerCase()
  if (kind !== 'percent' && kind !== 'amount') return null
  let value = Math.max(0, Number(raw.value) || 0)
  if (kind === 'percent') value = Math.min(100, value)
  if (value <= 0) return null
  return { kind: kind as DiscountIn['kind'], value }
}

export function applyDiscountCents(grossCents: number, discount: DiscountIn | null | undefined): number {
  const gross = Math.max(0, Number(grossCents) || 0)
  const d = normalizeDiscount(discount)
  if (!d) return gross
  if (d.kind === 'percent') {
    const off = Math.round((gross * d.value) / 100)
    return Math.max(0, gross - off)
  }
  return Math.max(0, gross - Math.min(gross, d.value))
}

export function lineGrossCents(
  line: MoneyLine,
  articles: Parameters<typeof articleEntry>[0],
  event: EdgeBundleEvent | null = null,
): number {
  const qty = Math.max(1, Number(line.qty) || 1)
  return lineUnitCents(line, articles, event) * qty
}

export function lineTotalCents(
  line: MoneyLine,
  articles: Parameters<typeof articleEntry>[0],
  event: EdgeBundleEvent | null = null,
): number {
  return applyDiscountCents(lineGrossCents(line, articles, event), line.discount)
}

export function orderSubtotalCents(
  lines: MoneyLine[] | null | undefined,
  articles: Parameters<typeof articleEntry>[0],
  event: EdgeBundleEvent | null = null,
): number {
  return (lines || []).reduce((s, l) => s + lineTotalCents(l, articles, event), 0)
}

export function orderTotalCents(
  lines: MoneyLine[] | null | undefined,
  orderDiscount: DiscountIn | null | undefined,
  articles: Parameters<typeof articleEntry>[0],
  event: EdgeBundleEvent | null = null,
): number {
  return applyDiscountCents(orderSubtotalCents(lines, articles, event), orderDiscount)
}

export function discountLabel(discount: DiscountIn | null | undefined): string {
  const d = normalizeDiscount(discount)
  if (!d) return ''
  if (d.kind === 'percent') return `Rabatt ${d.value}%`
  return `Rabatt ${formatAmount(d.value)}`
}

export function discountButtonLabel(discount: DiscountIn | null | undefined): string {
  const d = normalizeDiscount(discount)
  if (!d) return '%'
  if (d.kind === 'percent') return `−${d.value}%`
  return `−${formatAmount(d.value)}`
}
