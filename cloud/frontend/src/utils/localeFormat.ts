/** Map vue-i18n locale to BCP 47 tag for Intl formatters. */
export function intlLocale(locale: string): string {
  if (locale === 'de') return 'de-CH'
  if (locale === 'en') return 'en-CH'
  return locale || 'de-CH'
}

export function collatorLocale(locale: string): string {
  return intlLocale(locale)
}

export function formatMoney(cents: number | null | undefined, locale = 'de', currency = 'CHF'): string {
  const value = (cents || 0) / 100
  return new Intl.NumberFormat(intlLocale(locale), {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

export function formatAmount(cents: number | null | undefined, locale = 'de'): string {
  return new Intl.NumberFormat(intlLocale(locale), {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format((cents || 0) / 100)
}

/** Major currency units with ISO code prefix, e.g. "CHF 12.50". */
export function formatPriceWithCurrency(
  amount: number | string | null | undefined,
  currency: string,
  locale = 'de',
): string {
  const formatted = new Intl.NumberFormat(intlLocale(locale), {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(amount) || 0)
  return `${currency} ${formatted}`
}

export function formatDate(isoOrDate: string | Date | null | undefined, locale = 'de'): string {
  if (!isoOrDate) return '—'
  const d = isoOrDate instanceof Date ? isoOrDate : new Date(isoOrDate)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString(intlLocale(locale))
}

export function formatDateTime(
  isoOrDate: string | Date | null | undefined,
  locale = 'de',
  options: Intl.DateTimeFormatOptions = {},
): string {
  if (!isoOrDate) return '—'
  const d = isoOrDate instanceof Date ? isoOrDate : new Date(isoOrDate)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString(intlLocale(locale), {
    dateStyle: 'short',
    timeStyle: 'short',
    ...options,
  })
}

export function formatDateRange(
  startIso: string | null | undefined,
  endIso: string | null | undefined,
  locale = 'de',
): string {
  if (!startIso || !endIso) return '—'
  try {
    const start = formatDateTime(startIso, locale)
    const end = formatDateTime(endIso, locale)
    return `${start} – ${end}`
  } catch {
    return '—'
  }
}

export function formatTimeRange(
  startIso: string | null | undefined,
  endIso: string | null | undefined,
  locale = 'de',
): string {
  if (!startIso || !endIso) return '—'
  const start = new Date(startIso)
  const end = new Date(endIso)
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return '—'
  const intl = intlLocale(locale)
  const timeOptions: Intl.DateTimeFormatOptions = { hour: '2-digit', minute: '2-digit' }
  return `${start.toLocaleTimeString(intl, timeOptions)} – ${end.toLocaleTimeString(intl, timeOptions)}`
}
