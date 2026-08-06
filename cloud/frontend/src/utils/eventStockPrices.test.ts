import { describe, expect, it } from 'vitest'
import { eventPriceOverrideForSave, stockItemPriceFields } from './eventStockPrices'

describe('eventStockPrices', () => {
  it('maps empty Eventpreis to null (inherit org price)', () => {
    expect(eventPriceOverrideForSave(null)).toBeNull()
    expect(eventPriceOverrideForSave(undefined)).toBeNull()
    expect(eventPriceOverrideForSave('')).toBeNull()
  })

  it('keeps numeric Eventpreis including zero', () => {
    expect(eventPriceOverrideForSave(6.5)).toBe(6.5)
    expect(eventPriceOverrideForSave('1.25')).toBe(1.25)
    expect(eventPriceOverrideForSave(0)).toBe(0)
  })

  it('reads org_price and nullable override from API rows', () => {
    expect(stockItemPriceFields({ org_price: 5, price: null })).toEqual({
      org_price: 5,
      price: null,
    })
    expect(stockItemPriceFields({ org_price: 5, price: 6.5 })).toEqual({
      org_price: 5,
      price: 6.5,
    })
    expect(stockItemPriceFields({})).toEqual({ org_price: 0, price: null })
  })
})
