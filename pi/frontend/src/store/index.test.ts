import { beforeEach, describe, expect, it } from 'vitest'
import * as store from './index'
import {
  bundleWithRegisters,
  bundleWithStock,
  bundleWithWaiters,
  defaultBundle,
  discountsBundle,
} from '@tests/fixtures/bundle'
import { resetStore } from '@tests/helpers/resetStore'

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

  it('limits composite addition qty from ingredient stock', () => {
    const b = bundleWithStock()
    const ev = b.events![0]!
    ev.ingredients = {
      '1': { id: 1, name: 'Käse', monitor_stock: true, in_stock: 2 },
    }
    ev.articles!['20'] = {
      id: 20,
      name: 'Extra Käse',
      price: 1.0,
      is_addition: true,
      ingredients: [{ ingredient_id: 1, amount: 1 }],
      sellable: true,
    }
    store.bundle.value = b
    expect(store.availableAdditionQty(20)).toBe(2)
    store.addCartLine({
      article_id: 11,
      qty: 1,
      additions: [{ article_id: 20, qty: 1 }],
    })
    expect(store.availableAdditionQty(20)).toBe(1)
  })

  it('excludes the edited line when computing addition availability', () => {
    const b = bundleWithStock()
    const ev = b.events![0]!
    ev.articles!['20']!.in_stock = 2
    store.bundle.value = b
    store.addCartLine({
      article_id: 11,
      qty: 1,
      additions: [{ article_id: 20, qty: 2 }],
    })
    const lineId = store.cartLines.value[0].lineId
    expect(store.availableAdditionQty(20, lineId)).toBe(2)
  })
})

describe('lineQtyModalMax and availableQty for line edit', () => {
  beforeEach(() => {
    resetStore()
    store.bundle.value = bundleWithStock()
    store.selectedEventId.value = 1
    const ev = store.bundle.value!.events![0]!
    ev.articles!['40'] = {
      id: 40,
      name: 'Cervelat',
      price: 5.0,
      monitor_stock: true,
      in_stock: 17,
    }
  })

  it('modal max equals stock when editing line with qty 1', () => {
    store.addCartLine({ article_id: 40, qty: 1 })
    const lineId = store.cartLines.value[0].lineId
    const avail = store.availableQty(40, lineId)
    expect(avail).toBe(17)
    expect(store.lineQtyModalMax(avail)).toBe(17)
    expect(store.lineQtyModalMax(avail)).not.toBe(18)
  })

  it('returns ingredient-based availability for recipe articles', () => {
    const ev = store.bundle.value!.events![0]!
    ev.ingredients = {
      '1': { id: 1, name: 'Teig', monitor_stock: true, in_stock: 6 },
    }
    ev.articles!['50'] = {
      id: 50,
      name: 'Pizza',
      price: 12,
      ingredients: [{ ingredient_id: 1, amount: 2 }],
    }
    store.addCartLine({ article_id: 50, qty: 1 })
    expect(store.availableQty(50)).toBe(2)
    store.cartLines.value.push({
      lineId: 'V-1',
      kind: 'voucher_sale',
      voucher_definition_uuid: 'v-1',
      qty: 1,
      unit_cents: 1000,
    })
    expect(store.availableQty(50)).toBe(2)
  })
})

describe('isAdditionSellable', () => {
  beforeEach(() => {
    resetStore()
    store.bundle.value = bundleWithStock()
    store.selectedEventId.value = 1
  })

  it('returns false when direct article stock is zero', () => {
    const ev = store.bundle.value!.events![0]!
    ev.articles!['20'] = {
      id: 20,
      name: 'Zitrone',
      price: 1.0,
      is_addition: true,
      monitor_stock: true,
      in_stock: 0,
      sellable: false,
    }
    expect(store.isAdditionSellable(20)).toBe(false)
  })

  it('returns false when ingredient stock is exhausted', () => {
    const ev = store.bundle.value!.events![0]!
    ev.ingredients = {
      '1': { id: 1, name: 'Kartoffelsalat', monitor_stock: true, in_stock: 0 },
    }
    ev.articles!['20'] = {
      id: 20,
      name: 'mit Kartoffelsalat',
      price: 1.0,
      is_addition: true,
      ingredients: [{ ingredient_id: 1, amount: 0.5 }],
      sellable: false,
    }
    expect(store.isAdditionSellable(20)).toBe(false)
  })

  it('uses fallback metadata when addition is not in the article map', () => {
    expect(
      store.isAdditionSellable(99, null, {
        article_id: 99,
        name: 'Extra',
        sellable: true,
        monitor_stock: false,
      }),
    ).toBe(true)
    expect(
      store.isAdditionSellable(99, null, {
        article_id: 99,
        sellable: false,
      }),
    ).toBe(false)
  })

  it('rejects cart line with sold-out addition', () => {
    const ev = store.bundle.value!.events![0]!
    ev.articles!['20'] = {
      id: 20,
      name: 'Zitrone',
      price: 1.0,
      is_addition: true,
      monitor_stock: true,
      in_stock: 0,
      sellable: false,
    }
    expect(
      store.addCartLine({
        article_id: 11,
        qty: 1,
        additions: [{ article_id: 20, qty: 1 }],
      }),
    ).toBe(false)
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
    store.bundle.value!.events![0]!.configuration!.voucher_definitions = [
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

  it('rejects unknown vouchers and missing events', () => {
    expect(store.addVoucherCartLine({ voucher_definition_uuid: 'missing' })).toBe(false)
    store.selectedEventId.value = null
    expect(store.addVoucherCartLine({ voucher_definition_uuid: 'v-1' })).toBe(false)
  })
})

describe('cart helpers and admin state', () => {
  beforeEach(() => {
    resetStore()
    store.bundle.value = defaultBundle()
    store.selectedEventId.value = 1
  })

  it('clears cart lines and order discount', () => {
    store.addCartLine({ article_id: 10, qty: 1 })
    store.setOrderDiscount({ kind: 'amount', value: 100 })
    store.clearCart()
    expect(store.cartLines.value).toHaveLength(0)
    expect(store.orderDiscount.value).toBeNull()
  })

  it('removes a cart line by id', () => {
    store.addCartLine({ article_id: 10, qty: 1 })
    const lineId = store.cartLines.value[0].lineId
    store.removeCartLine(lineId)
    expect(store.cartLines.value).toHaveLength(0)
  })

  it('exposes article names and cart labels', () => {
    expect(store.articleName(10)).toBe('Bier')
    expect(store.articleName(999)).toBe('Artikel #999')
    store.addCartLine({ article_id: 10, qty: 2 })
    expect(store.cartLineLabel(store.cartLines.value[0])).toBe('Bier')
    expect(store.cartCount.value).toBe(2)
  })

  it('reports bundle and admin pin requirements', () => {
    expect(store.bundleReady()).toBe(true)
    store.bundle.value = null
    expect(store.bundleReady()).toBe(false)
    store.bundle.value = { ...defaultBundle(), admin_pin_hashes: ['hash'] }
    expect(store.adminRequiresPin()).toBe(true)
    store.setAdminUnlocked(true)
    expect(store.adminUnlocked.value).toBe(true)
    store.clearAdminSession()
    expect(store.adminUnlocked.value).toBe(false)
  })
})

describe('register session validation', () => {
  beforeEach(() => {
    resetStore()
  })

  it('refreshes register session from bundle configuration', () => {
    store.bundle.value = bundleWithRegisters()
    store.selectedEventId.value = 1
    store.registerSession.value = { uuid: 'register-1', name: 'Old name' }
    store.validateRegisterSession()
    expect(store.registerSession.value).toEqual({ uuid: 'register-1', name: 'Kasse 1' })
  })

  it('setRegisterSession clears waiter and cart', () => {
    store.bundle.value = bundleWithWaiters()
    store.selectedEventId.value = 1
    store.waiter.value = { uuid: 'waiter-1', name: 'Anna' }
    store.cartLines.value = [{ lineId: 'L-1', article_id: 10, qty: 1 }]
    store.setRegisterSession({ uuid: 'register-1', name: 'Kasse 1' })
    expect(store.waiter.value).toBeNull()
    expect(store.cartLines.value).toHaveLength(0)
    expect(store.registerSession.value?.uuid).toBe('register-1')
  })
})

describe('waiter session validation', () => {
  beforeEach(() => {
    resetStore()
  })

  it('refreshes waiter session from bundle configuration', () => {
    store.bundle.value = bundleWithWaiters()
    store.selectedEventId.value = 1
    store.waiter.value = { uuid: 'waiter-1', name: 'Old' }
    store.validateWaiterSession()
    expect(store.waiter.value).toEqual({ uuid: 'waiter-1', name: 'Anna' })
  })
})

describe('addCartLine edge cases', () => {
  beforeEach(() => {
    resetStore()
    store.bundle.value = bundleWithStock()
    store.selectedEventId.value = 1
  })

  it('rejects unsellable additions', () => {
    store.bundle.value!.events![0]!.articles![20]!.sellable = false
    expect(
      store.addCartLine({
        article_id: 11,
        qty: 1,
        additions: [{ article_id: 20, qty: 1 }],
      }),
    ).toBe(false)
  })

  it('rejects when addition stock is insufficient', () => {
    expect(
      store.addCartLine({
        article_id: 11,
        qty: 2,
        additions: [{ article_id: 20, qty: 2 }],
      }),
    ).toBe(false)
  })

  it('merges lines with matching station and additions', () => {
    expect(
      store.addCartLine({
        article_id: 10,
        qty: 1,
        station_uuid: 'st-1',
        additions: [{ article_id: 20, qty: 1 }],
      }),
    ).toBe(true)
    expect(
      store.addCartLine({
        article_id: 10,
        qty: 1,
        station_uuid: 'st-1',
        additions: [{ article_id: 20, qty: 1 }],
      }),
    ).toBe(true)
    expect(store.cartLines.value).toHaveLength(1)
    expect(store.cartLines.value[0].qty).toBe(2)
  })

  it('shows ingredient name when recipe article is sold out', () => {
    const ev = store.bundle.value!.events![0]!
    ev.ingredients = {
      '1': { id: 1, name: 'Teig', monitor_stock: true, in_stock: 0 },
    }
    ev.articles!['50'] = {
      id: 50,
      name: 'Pizza',
      price: 12,
      ingredients: [{ ingredient_id: 1, amount: 1 }],
    }
    expect(store.addCartLine({ article_id: 50, qty: 1 })).toBe(false)
    expect(store.toast.value?.message).toBe('Teig ausverkauft')
  })

  it('caps recipe article qty and names limiting ingredient', () => {
    const ev = store.bundle.value!.events![0]!
    ev.ingredients = {
      '1': { id: 1, name: 'Teig', monitor_stock: true, in_stock: 3 },
    }
    ev.articles!['50'] = {
      id: 50,
      name: 'Pizza',
      price: 12,
      ingredients: [{ ingredient_id: 1, amount: 1 }],
    }
    expect(store.addCartLine({ article_id: 50, qty: 5 })).toBe(true)
    expect(store.cartLines.value[0].qty).toBe(3)
    expect(store.toast.value?.message).toContain('Engpass: Teig')
  })

  it('rejects ingredient-based additions when stock is insufficient', () => {
    const ev = store.bundle.value!.events![0]!
    ev.ingredients = {
      '1': { id: 1, name: 'Käse', monitor_stock: true, in_stock: 1 },
    }
    ev.articles!['20'] = {
      id: 20,
      name: 'Extra Käse',
      price: 1,
      is_addition: true,
      ingredients: [{ ingredient_id: 1, amount: 1 }],
      sellable: true,
    }
    expect(
      store.addCartLine({
        article_id: 11,
        qty: 2,
        additions: [{ article_id: 20, qty: 1 }],
      }),
    ).toBe(false)
    expect(store.toast.value?.message).toContain('Engpass: Käse')
  })
})

describe('patchEventArticles and stockArticlesForEvent', () => {
  beforeEach(() => {
    resetStore()
    store.bundle.value = bundleWithStock()
    store.selectedEventId.value = 1
  })

  it('patches article stock on the active event', () => {
    store.patchEventArticles(1, { 10: { in_stock: 1 } })
    expect(store.bundle.value!.events![0]!.articles![10]!.in_stock).toBe(1)
    expect(store.availableQty(10)).toBe(1)
  })

  it('lists monitored stock articles sorted by name', () => {
    const ev = store.bundle.value!.events![0]!
    ev.articles![30] = { id: 30, name: 'Apfel', price: 0, monitor_stock: true, in_stock: 4 }
    expect(store.stockArticlesForEvent(ev).map((a) => a.name)).toEqual(['Apfel', 'Bier', 'Zitrone'])
    expect(store.stockArticlesForEvent({} as Parameters<typeof store.stockArticlesForEvent>[0])).toEqual([])
  })
})
