import { lineIdentityKeyFromItem } from './bundleHelpers'

/** Swiss number format: 1'234.56 (apostrophe thousands, dot decimals). */
export const MONEY_LOCALE = 'de-CH'

const amountFormatter = new Intl.NumberFormat(MONEY_LOCALE, {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

/** Cents → amount string without currency symbol. */
export function formatAmount(cents) {
  return amountFormatter.format((cents || 0) / 100)
}

/** @param {number} cents
 *  @param {string} [_currency] ignored — event currency is implicit in the UI */
export function formatMoney(cents, _currency) {
  return formatAmount(cents)
}

/** Major currency units (e.g. article.price) without currency symbol. */
export function formatPrice(amount) {
  return amountFormatter.format(Number(amount) || 0)
}

function articleEntry(articles, articleId) {
  return articles?.[String(articleId)] || articles?.[articleId]
}

function additionPriceCents(articles, baseArticle, additionId) {
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

export function articleBaseUnitCents(articles, articleId) {
  const base = articleEntry(articles, articleId)
  return base ? Math.round(Number(base.price || 0) * 100) : 0
}

/** One entitled item: base catalog price, or full line unit when include_additions is set. */
export function voucherEntitlementCreditCents(sel, articles, vd, event = null, lineGroups = null) {
  if (vd?.include_additions) {
    if (lineGroups?.length) {
      const key = lineIdentityKeyFromItem(sel)
      const g = lineGroups.find((x) => lineIdentityKeyFromItem(x) === key)
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

export function lineUnitCents(line, articles, event = null) {
  if (line?.kind === 'voucher_sale') {
    if (line.unit_cents != null) return Math.max(0, Number(line.unit_cents))
    const defs = event?.configuration?.voucher_definitions || []
    const vUuid = String(line.voucher_definition_uuid || '')
    const vd = defs.find((d) => String(d.uuid) === vUuid)
    return Math.max(0, Number(vd?.value_cents) || 0)
  }
  // Snapshotted / API lines: unit_cents is already base + additions per unit.
  if (line?.unit_cents != null) return Math.max(0, Number(line.unit_cents))
  const base = articleEntry(articles, line.article_id)
  let unit = base ? Math.round(Number(base.price || 0) * 100) : 0
  for (const add of line.additions || []) {
    const addQty = Math.max(1, Number(add.qty) || 1)
    unit += additionPriceCents(articles, base, add.article_id) * addQty
  }
  return Math.max(0, unit)
}

export function discountsEnabled(event) {
  return Boolean(event?.discounts_enabled)
}

export function normalizeDiscount(raw) {
  if (!raw || typeof raw !== 'object') return null
  const kind = String(raw.kind || '').toLowerCase()
  if (kind !== 'percent' && kind !== 'amount') return null
  let value = Math.max(0, Number(raw.value) || 0)
  if (kind === 'percent') value = Math.min(100, value)
  if (value <= 0) return null
  return { kind, value }
}

export function applyDiscountCents(grossCents, discount) {
  const gross = Math.max(0, Number(grossCents) || 0)
  const d = normalizeDiscount(discount)
  if (!d) return gross
  if (d.kind === 'percent') {
    const off = Math.round((gross * d.value) / 100)
    return Math.max(0, gross - off)
  }
  return Math.max(0, gross - Math.min(gross, d.value))
}

export function lineGrossCents(line, articles, event = null) {
  const qty = Math.max(1, Number(line.qty) || 1)
  return lineUnitCents(line, articles, event) * qty
}

export function lineTotalCents(line, articles, event = null) {
  return applyDiscountCents(lineGrossCents(line, articles, event), line.discount)
}

export function orderSubtotalCents(lines, articles, event = null) {
  return (lines || []).reduce((s, l) => s + lineTotalCents(l, articles, event), 0)
}

export function orderTotalCents(lines, orderDiscount, articles, event = null) {
  return applyDiscountCents(orderSubtotalCents(lines, articles, event), orderDiscount)
}

export function discountLabel(discount) {
  const d = normalizeDiscount(discount)
  if (!d) return ''
  if (d.kind === 'percent') return `Rabatt ${d.value}%`
  return `Rabatt ${formatAmount(d.value)}`
}

export function discountButtonLabel(discount) {
  const d = normalizeDiscount(discount)
  if (!d) return '%'
  if (d.kind === 'percent') return `−${d.value}%`
  return `−${formatAmount(d.value)}`
}
