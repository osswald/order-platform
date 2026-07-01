import { describe, expect, it } from 'vitest'
import { formatMoney, formatPriceWithCurrency } from './localeFormat'

describe('localeFormat money', () => {
  it('prefixes ISO currency before formatted amount', () => {
    expect(formatMoney(1250, 'de', 'CHF', 'CH')).toBe('CHF 12.50')
    expect(formatMoney(1250, 'en', 'CHF', 'CH')).toBe('CHF 12.50')
    expect(formatPriceWithCurrency(12.5, 'CHF', 'de', 'CH')).toBe('CHF 12.50')
  })

  it('uses German decimal separator for DE organisations', () => {
    expect(formatMoney(1250, 'de', 'EUR', 'DE')).toBe('EUR 12,50')
  })
})
