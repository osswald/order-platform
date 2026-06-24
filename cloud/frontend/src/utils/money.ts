import { formatAmount as formatAmountLocale } from './localeFormat'
import { i18n } from '@/i18n'

/** Amount in major units from cents, Swiss format without currency symbol. */
export function formatAmount(cents: number | null | undefined): string {
  return formatAmountLocale(cents, i18n.global.locale.value)
}
