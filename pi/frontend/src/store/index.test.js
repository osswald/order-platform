import { beforeEach, describe, expect, it } from 'vitest'
import * as store from './index'
import {
  bundleWithRegisters,
  bundleWithStock,
  bundleWithWaiters,
  defaultBundle,
  discountsBundle,
} from '../../tests/fixtures/bundle'
import { resetStore } from '../../tests/helpers/resetStore'

describe('addCartLine', () => {
  beforeEach(() => {
    resetStore()
    store.bundle.value = defaultBundle()
    store.selectedEventId.value = 1
  })

  it('merges identical lines by incrementing qty', () => {
    expect(store.addCartLine({ article_id: 10, qty: 1 })).toBe(true)
    expect(store.addCartLine({ article_id: 10, qty: 2 })).toBe(true)
    expect(store.cartLines.value).toHaveLength(1)
    expect(store.cartLines.value[0].qty).toBe(3)
  })

  it('creates separate lines when note differs', () => {
    store.addCartLine({ article_id: 10, qty: 1, note: 'A' })
    store.addCartLine({ article_id: 10, qty: 1, note: 'B' })
    expect(store.cartLines.value).toHaveLength(2)
  })

  it('rejects when stock is exhausted', () => {
    store.bundle.value = bundleWithStock()
    store.addCartLine({ article_id: 10, qty: 3 })
    expect(store.addCartLine({ article_id: 10, qty: 1 })).toBe(false)
    expect(store.cartLines.value[0].qty).toBe(3)
  })

  it('caps qty when request exceeds available stock', () => {
    store.bundle.value = bundleWithStock()
    expect(store.addCartLine({ article_id: 10, qty: 5 })).toBe(true)
    expect(store.cartLines.value[0].qty).toBe(3)
  })

  it('tracks addition stock across cart lines', () => {
    store.bundle.value = bundleWithStock()
    store.addCartLine({
      article_id: 11,
      qty: 1,
      additions: [{ article_id: 20, qty: 2 }],
    })
    expect(store.cartQtyForAddition(20)).toBe(2)
    expect(store.availableAdditionQty(20)).toBe(0)
  })
})

describe('session validation', () => {
  beforeEach(() => {
    resetStore()
  })

  it('clears stale waiter when not in bundle', () => {
    store.bundle.value = defaultBundle()
    store.selectedEventId.value = 1
    store.waiter.value = { uuid: 'missing', name: 'Ghost' }
    store.validateWaiterSession()
    expect(store.waiter.value).toBeNull()
    expect(store.selectedEventId.value).toBeNull()
  })

  it('setWaiter clears register session and cart', () => {
    store.bundle.value = bundleWithRegisters()
    store.selectedEventId.value = 1
    store.registerSession.value = { uuid: 'register-1', name: 'Kasse 1' }
    store.cartLines.value = [{ lineId: 'L-1', article_id: 10, qty: 1 }]
    store.setWaiter({ uuid: 'waiter-1', name: 'Anna' })
    expect(store.registerSession.value).toBeNull()
    expect(store.cartLines.value).toHaveLength(0)
    expect(store.waiter.value).toEqual({ uuid: 'waiter-1', name: 'Anna' })
  })
})

describe('cart totals', () => {
  beforeEach(() => {
    resetStore()
    store.bundle.value = discountsBundle()
    store.selectedEventId.value = 1
  })

  it('matches money.js computed totals', () => {
    store.addCartLine({ article_id: 10, qty: 2 })
    store.updateCartLine(store.cartLines.value[0].lineId, {
      discount: { kind: 'percent', value: 10 },
    })
    store.addCartLine({ article_id: 10, qty: 1 })
    store.setOrderDiscount({ kind: 'amount', value: 200 })
    expect(store.cartSubtotalCents.value).toBe(1400)
    expect(store.cartTotalCents.value).toBe(1200)
  })
})

describe('updateCartLine and decrementCartLine', () => {
  beforeEach(() => {
    resetStore()
    store.bundle.value = defaultBundle()
    store.selectedEventId.value = 1
    store.addCartLine({ article_id: 10, qty: 3 })
  })

  it('patches line fields and clears discount when undefined', () => {
    const lineId = store.cartLines.value[0].lineId
    store.updateCartLine(lineId, { discount: { kind: 'percent', value: 5 } })
    expect(store.cartLines.value[0].discount).toEqual({ kind: 'percent', value: 5 })
    store.updateCartLine(lineId, { discount: undefined })
    expect(store.cartLines.value[0].discount).toBeUndefined()
  })

  it('decrements qty and removes line at one', () => {
    const lineId = store.cartLines.value[0].lineId
    store.decrementCartLine(lineId)
    expect(store.cartLines.value[0].qty).toBe(2)
    store.decrementCartLine(lineId)
    store.decrementCartLine(lineId)
    expect(store.cartLines.value).toHaveLength(0)
  })
})

describe('addVoucherCartLine', () => {
  beforeEach(() => {
    resetStore()
    store.bundle.value = defaultBundle()
    store.bundle.value.events[0].configuration.voucher_definitions = [
      { uuid: 'v-1', kind: 'fixed_amount', name: 'Gutschein', value_cents: 2000 },
    ]
    store.selectedEventId.value = 1
  })

  it('adds and merges voucher sale lines', () => {
    expect(store.addVoucherCartLine({ voucher_definition_uuid: 'v-1', qty: 1 })).toBe(true)
    expect(store.addVoucherCartLine({ voucher_definition_uuid: 'v-1', qty: 2 })).toBe(true)
    expect(store.cartLines.value).toHaveLength(1)
    expect(store.cartLines.value[0].qty).toBe(3)
    expect(store.cartLines.value[0].unit_cents).toBe(2000)
  })
})
