import { describe, expect, it } from 'vitest'
import { kitchenViewModeFromSlug, kitchenViewSlugFromMode } from './kitchenMonitorViewSlug'

describe('kitchenViewModeFromSlug', () => {
  it('maps produkte to products view', () => {
    expect(kitchenViewModeFromSlug('produkte')).toBe('products')
    expect(kitchenViewModeFromSlug('PRODUKTE')).toBe('products')
  })

  it('defaults missing or unknown slugs to orders', () => {
    expect(kitchenViewModeFromSlug(undefined)).toBe('orders')
    expect(kitchenViewModeFromSlug('bestellungen')).toBe('orders')
    expect(kitchenViewModeFromSlug('foo')).toBe('orders')
  })
})

describe('kitchenViewSlugFromMode', () => {
  it('maps view modes to German URL segments', () => {
    expect(kitchenViewSlugFromMode('products')).toBe('produkte')
    expect(kitchenViewSlugFromMode('orders')).toBe('bestellungen')
  })
})
