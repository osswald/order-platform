import { i18n } from '@/i18n'
import { resolveFormatLocale } from './formatLocale'

function formatLocaleTag(uiLocale: string, countryCode?: string | null): string {
  return resolveFormatLocale(uiLocale, countryCode)
}

function formatDecimal(
  cents: number | null | undefined,
  uiLocale: string,
  countryCode?: string | null,
): string {
  const formatLocale = formatLocaleTag(uiLocale, countryCode)
  return i18n.global.n((cents || 0) / 100, { key: 'decimal', locale: formatLocale })
}

export { collatorLocale, intlLocale, resolveFormatLocale } from './formatLocale'

export function formatMoney(
  cents: number | null | undefined,
  locale = 'de',
  currency = 'CHF',
  countryCode?: string | null,
): string {
  const code = (currency || 'CHF').toUpperCase()
  return `${code} ${formatDecimal(cents, locale, countryCode)}`
}

export function formatAmount(
  cents: number | null | undefined,
  locale = 'de',
  countryCode?: string | null,
): string {
  return formatDecimal(cents, locale, countryCode)
}

/** Major currency units with ISO code prefix, e.g. "CHF 12.50". */
export function formatPriceWithCurrency(
  amount: number | string | null | undefined,
  currency: string,
  locale = 'de',
  countryCode?: string | null,
): string {
  const code = (currency || 'CHF').toUpperCase()
  const formatLocale = formatLocaleTag(locale, countryCode)
  const value = Number(amount) || 0
  const formatted = i18n.global.n(value, { key: 'decimal', locale: formatLocale })
  return `${code} ${formatted}`
}

function parseDate(isoOrDate: string | Date | null | undefined): Date | null {
  if (!isoOrDate) return null
  const d = isoOrDate instanceof Date ? isoOrDate : new Date(isoOrDate)
  return Number.isNaN(d.getTime()) ? null : d
}

export function formatDate(
  isoOrDate: string | Date | null | undefined,
  locale = 'de',
  countryCode?: string | null,
): string {
  const d = parseDate(isoOrDate)
  if (!d) return '—'
  const formatLocale = formatLocaleTag(locale, countryCode)
  return i18n.global.d(d, { key: 'date', locale: formatLocale })
}

export function formatDateTime(
  isoOrDate: string | Date | null | undefined,
  locale = 'de',
  countryCode?: string | null,
): string {
  const d = parseDate(isoOrDate)
  if (!d) return '—'
  const formatLocale = formatLocaleTag(locale, countryCode)
  return i18n.global.d(d, { key: 'short', locale: formatLocale })
}

export function formatDateRange(
  startIso: string | null | undefined,
  endIso: string | null | undefined,
  locale = 'de',
  countryCode?: string | null,
): string {
  if (!startIso || !endIso) return '—'
  const start = formatDateTime(startIso, locale, countryCode)
  const end = formatDateTime(endIso, locale, countryCode)
  if (start === '—' && end === '—') return '—'
  return `${start} – ${end}`
}

export function formatTimeRange(
  startIso: string | null | undefined,
  endIso: string | null | undefined,
  locale = 'de',
  countryCode?: string | null,
): string {
  if (!startIso || !endIso) return '—'
  const start = parseDate(startIso)
  const end = parseDate(endIso)
  if (!start || !end) return '—'
  const formatLocale = formatLocaleTag(locale, countryCode)
  const startText = i18n.global.d(start, { key: 'time', locale: formatLocale })
  const endText = i18n.global.d(end, { key: 'time', locale: formatLocale })
  return `${startText} – ${endText}`
}
