/** Partial-quantity basket cents for one split-pay line group. */
export function groupBasketCents(g) {
  const qty = Math.max(0, Number(g.basketQty) || 0)
  const totalQty = Math.max(1, Number(g.totalQty) || 1)
  const lineTotal = Math.max(0, Number(g.lineTotalCents) || 0)
  if (lineTotal > 0) {
    return Math.round((lineTotal / totalQty) * qty)
  }
  return Math.max(0, Number(g.unitCents) || 0) * qty
}

export function sumGroupBasketCents(groups) {
  return (groups || []).reduce((s, g) => s + groupBasketCents(g), 0)
}

export function sumVoucherCreditCents(redemptions) {
  return (redemptions || []).reduce(
    (s, r) => s + Math.max(0, Number(r.applied_cents) || 0),
    0,
  )
}

export function basketCentsAfterVoucher(rawBasketCents, voucherCreditCents) {
  return Math.max(0, Number(rawBasketCents) - Number(voucherCreditCents))
}
