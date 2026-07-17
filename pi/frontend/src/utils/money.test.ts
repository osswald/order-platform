import { describe, expect, it } from 'vitest'
import type { DiscountIn, EdgeBundleArticle, EdgeBundleEvent } from '@/types/api'
import {
  applyDiscountCents,
  discountButtonLabel,
  discountLabel,
  discountsEnabled,
  formatAmount,
  formatMoney,
  formatPrice,
  lineGrossCents,
  lineTotalCents,
  lineUnitCents,
  normalizeDiscount,
  orderSubtotalCents,
  orderTotalCents,
  voucherEntitlementCreditCents,
  type MoneyLine,
} from './money'

describe('applyDiscountCents', () => {
  it('applies percent and amount discounts', () => {
    expect(applyDiscountCents(1000, { kind: 'percent', value: 10 })).toBe(900)
    expect(applyDiscountCents(1000, { kind: 'amount', value: 250 })).toBe(750)
    expect(applyDiscountCents(100, { kind: 'amount', value: 500 })).toBe(0)
  })
})

describe('line and order totals', () => {
  const arts = { 10: { id: 10, name: 'Bier', price: 5.0, additions: [] } } as Record<
    string,
    EdgeBundleArticle
  >
  const ev = { discounts_enabled: true } as unknown as EdgeBundleEvent
  const lines: MoneyLine[] = [
    { article_id: 10, qty: 2, discount: { kind: 'percent', value: 10 } },
    { article_id: 10, qty: 1 },
  ]

  it('matches backend test_line_and_order_totals', () => {
    expect(lineGrossCents(lines[0], arts)).toBe(1000)
    expect(lineTotalCents(lines[0], arts)).toBe(900)
    expect(orderSubtotalCents(lines, arts, ev)).toBe(1400)
    expect(orderTotalCents(lines, { kind: 'amount', value: 200 }, arts, ev)).toBe(1200)
  })
})

describe('lineUnitCents', () => {
  it('does not double-count addition prices on snapshotted lines', () => {
    const arts = {
      1: {
        id: 1,
        name: 'Article A',
        price: 8.0,
        additions: [{ article_id: 2, name: 'Addon B', price: 3.0 }],
      },
      2: { id: 2, name: 'Addon B', price: 3.0 },
    } as unknown as Record<string, EdgeBundleArticle>
    const raw = { article_id: 1, qty: 1, additions: [{ article_id: 2, qty: 1 }] }
    expect(lineUnitCents(raw, arts)).toBe(1100)

    const snap = { ...raw, unit_cents: 1100, additions: [{ article_id: 2, qty: 1, unit_cents: 300 }] }
    expect(lineUnitCents(snap, arts)).toBe(1100)
    expect(lineTotalCents(snap, arts)).toBe(1100)
  })

  it('uses voucher definition value for voucher_sale lines', () => {
    const ev = {
      configuration: {
        voucher_definitions: [{ uuid: 'v-1', value_cents: 2500 }],
      },
    } as unknown as EdgeBundleEvent
    const line = { kind: 'voucher_sale', voucher_definition_uuid: 'v-1', qty: 1 }
    expect(lineUnitCents(line, {}, ev)).toBe(2500)
  })

  it('prefers snapshotted unit_cents on the line', () => {
    expect(lineUnitCents({ article_id: 1, unit_cents: 999 }, {})).toBe(999)
  })
})

describe('normalizeDiscount', () => {
  it('rejects invalid discount kinds and zero values', () => {
    expect(normalizeDiscount(null)).toBeNull()
    expect(normalizeDiscount({ kind: 'bogus', value: 10 } as unknown as DiscountIn)).toBeNull()
    expect(normalizeDiscount({ kind: 'percent', value: 0 })).toBeNull()
    expect(normalizeDiscount({ kind: 'percent', value: 150 })).toEqual({ kind: 'percent', value: 100 })
  })

  it('accepts amount discounts', () => {
    expect(normalizeDiscount({ kind: 'amount', value: 250 })).toEqual({ kind: 'amount', value: 250 })
  })
})

describe('discount labels', () => {
  it('formats percent and amount discount labels', () => {
    expect(discountLabel({ kind: 'percent', value: 10 })).toBe('Rabatt 10%')
    expect(discountLabel({ kind: 'amount', value: 250 })).toBe("Rabatt 2.50")
    expect(discountLabel(null)).toBe('')
    expect(discountButtonLabel({ kind: 'percent', value: 10 })).toBe('−10%')
    expect(discountButtonLabel({ kind: 'amount', value: 250 })).toBe('−2.50')
    expect(discountButtonLabel(null)).toBe('%')
  })
})

describe('format helpers', () => {
  it('formats money and price strings', () => {
    expect(formatMoney(500, 'CHF')).toBe('CHF 5.00')
    expect(formatPrice(12.5, 'CHF')).toBe('CHF 12.50')
  })
})

describe('discountsEnabled', () => {
  it('reads the event flag', () => {
    expect(discountsEnabled({ discounts_enabled: true } as unknown as EdgeBundleEvent)).toBe(true)
    expect(discountsEnabled({} as unknown as EdgeBundleEvent)).toBe(false)
  })
})

describe('formatAmount', () => {
  it('formats Swiss locale without currency symbol', () => {
    expect(formatAmount(123456)).toBe("1'234.56")
    expect(formatAmount(0)).toBe('0.00')
  })
})

describe('voucherEntitlementCreditCents', () => {
  const arts = {
    1: {
      id: 1,
      price: 8.0,
      additions: [{ article_id: 2, price: 3.0 }],
    },
    2: { id: 2, price: 3.0 },
  } as unknown as Record<string, EdgeBundleArticle>

  it('returns base price when include_additions is false', () => {
    const sel = { article_id: 1, additions: [{ article_id: 2, qty: 1 }] }
    expect(voucherEntitlementCreditCents(sel, arts, { include_additions: false })).toBe(800)
  })

  it('returns full line unit when include_additions is true', () => {
    const sel = { article_id: 1, additions: [{ article_id: 2, qty: 1 }] }
    expect(voucherEntitlementCreditCents(sel, arts, { include_additions: true })).toBe(1100)
  })

  it('uses line group unit_cents when provided', () => {
    const sel = { article_id: 1, additions: [] }
    const lineGroups = [{ article_id: 1, note: '', additions: [], unit_cents: 999 }]
    expect(
      voucherEntitlementCreditCents(sel, arts, { include_additions: true }, null, lineGroups),
    ).toBe(999)
  })
})
