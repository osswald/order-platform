import { describe, expect, it } from 'vitest'
import {
  basketCentsAfterVoucher,
  groupBasketCents,
  sumGroupBasketCents,
  sumVoucherCreditCents,
} from './splitPay'

describe('groupBasketCents', () => {
  it('rounds partial qty from discounted line total (900 / 3 * 1 = 300)', () => {
    expect(
      groupBasketCents({
        basketQty: 1,
        totalQty: 3,
        lineTotalCents: 900,
        unitCents: 500,
      }),
    ).toBe(300)
  })

  it('settles full discounted line (900 / 2 * 2 = 900)', () => {
    expect(
      groupBasketCents({
        basketQty: 2,
        totalQty: 2,
        lineTotalCents: 900,
        unitCents: 500,
      }),
    ).toBe(900)
  })

  it('falls back to unitCents when lineTotalCents is zero', () => {
    expect(
      groupBasketCents({
        basketQty: 2,
        totalQty: 4,
        lineTotalCents: 0,
        unitCents: 250,
      }),
    ).toBe(500)
  })

  it('returns zero for empty basket qty', () => {
    expect(
      groupBasketCents({
        basketQty: 0,
        totalQty: 2,
        lineTotalCents: 900,
        unitCents: 500,
      }),
    ).toBe(0)
  })
})

describe('sumGroupBasketCents', () => {
  it('sums multiple groups', () => {
    const groups = [
      { basketQty: 1, totalQty: 2, lineTotalCents: 900, unitCents: 500 },
      { basketQty: 1, totalQty: 1, lineTotalCents: 0, unitCents: 300 },
    ]
    expect(sumGroupBasketCents(groups)).toBe(750)
  })
})

describe('voucher credit', () => {
  it('sums applied voucher cents', () => {
    expect(
      sumVoucherCreditCents([
        { applied_cents: 200 },
        { applied_cents: 50 },
        { applied_cents: -10 },
      ]),
    ).toBe(250)
  })

  it('subtracts voucher credit from raw basket total', () => {
    expect(basketCentsAfterVoucher(900, 200)).toBe(700)
    expect(basketCentsAfterVoucher(100, 500)).toBe(0)
  })
})
