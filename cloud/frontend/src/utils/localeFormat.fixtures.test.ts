import { describe, expect, it } from 'vitest'
import fixtures from '../../../shared/format-fixtures.json'
import { i18n } from '@/i18n'
import { resolveFormatLocale } from './formatLocale'
import { formatAmount, formatMoney } from './localeFormat'

describe('localeFormat contract fixtures', () => {
  it('matches shared format_locale cases', () => {
    for (const case_ of fixtures.format_locale) {
      expect(resolveFormatLocale(case_.ui_locale, case_.country_code)).toBe(case_.intl_locale)
    }
  })

  it('matches shared money cases', () => {
    for (const case_ of fixtures.money) {
      const country = case_.country_code
      const amount = formatAmount(case_.cents, case_.ui_locale, country)
      const money = formatMoney(case_.cents, case_.ui_locale, case_.currency, country)
      if ('expected_amount' in case_ && case_.expected_amount != null) {
        expect(amount).toBe(case_.expected_amount)
      }
      if ('expected_money' in case_ && case_.expected_money != null) {
        expect(money).toBe(case_.expected_money)
      }
      if ('expected_amount_suffix' in case_ && case_.expected_amount_suffix != null) {
        expect(amount.endsWith(case_.expected_amount_suffix)).toBe(true)
      }
      if ('expected_money_prefix' in case_ && case_.expected_money_prefix != null) {
        expect(money.startsWith(case_.expected_money_prefix)).toBe(true)
      }
    }
  })

  it('formats decimals via vue-i18n numberFormats', () => {
    const formatted = i18n.global.n(12.5, { key: 'decimal', locale: 'de-CH' })
    expect(formatted).toBe('12.50')
  })
})
