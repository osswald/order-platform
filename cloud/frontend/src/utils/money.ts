import { formatAmount as formatAmountLocale, formatMoney as formatMoneyLocale } from './localeFormat'
import { i18n } from '@/i18n'

/** Amount in major units from cents, without currency code. */
export function formatAmount(
  cents: number | null | undefined,
  countryCode?: string | null,
): string {
  return formatAmountLocale(cents, i18n.global.locale.value, countryCode)
}

/** Cents with ISO currency code prefix, e.g. "CHF 12.50". */
export function formatMoney(
  cents: number | null | undefined,
  currency = 'CHF',
  countryCode?: string | null,
): string {
  return formatMoneyLocale(cents, i18n.global.locale.value, currency, countryCode)
}
