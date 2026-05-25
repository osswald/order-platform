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

export function lineUnitCents(line, articles, event = null) {
  if (line?.kind === 'voucher_sale') {
    if (line.unit_cents != null) return Math.max(0, Number(line.unit_cents))
    const defs = event?.configuration?.voucher_definitions || []
    const vUuid = String(line.voucher_definition_uuid || '')
    const vd = defs.find((d) => String(d.uuid) === vUuid)
    return Math.max(0, Number(vd?.value_cents) || 0)
  }
  const base = articleEntry(articles, line.article_id)
  let unit = base ? Math.round(Number(base.price || 0) * 100) : 0
  for (const add of line.additions || []) {
    const addQty = Math.max(1, Number(add.qty) || 1)
    unit += additionPriceCents(articles, base, add.article_id) * addQty
  }
  return Math.max(0, unit)
}

export function lineTotalCents(line, articles, event = null) {
  const qty = Math.max(1, Number(line.qty) || 1)
  return lineUnitCents(line, articles, event) * qty
}
