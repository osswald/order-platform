/** Map vue-i18n locale to BCP 47 tag for Intl formatters. */
export function intlLocale(locale) {
  if (locale === 'de') return 'de-CH'
  if (locale === 'en') return 'en-CH'
  return locale || 'de-CH'
}

export function collatorLocale(locale) {
  return intlLocale(locale)
}

export function formatMoney(cents, locale = 'de', currency = 'CHF') {
  const value = (cents || 0) / 100
  return new Intl.NumberFormat(intlLocale(locale), {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

export function formatAmount(cents, locale = 'de') {
  return new Intl.NumberFormat(intlLocale(locale), {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format((cents || 0) / 100)
}

/** Major currency units with ISO code prefix, e.g. "CHF 12.50". */
export function formatPriceWithCurrency(amount, currency, locale = 'de') {
  const formatted = new Intl.NumberFormat(intlLocale(locale), {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(amount) || 0)
  return `${currency} ${formatted}`
}

export function formatDate(isoOrDate, locale = 'de') {
  if (!isoOrDate) return '—'
  const d = isoOrDate instanceof Date ? isoOrDate : new Date(isoOrDate)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString(intlLocale(locale))
}

export function formatDateTime(isoOrDate, locale = 'de', options = {}) {
  if (!isoOrDate) return '—'
  const d = isoOrDate instanceof Date ? isoOrDate : new Date(isoOrDate)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString(intlLocale(locale), {
    dateStyle: 'short',
    timeStyle: 'short',
    ...options,
  })
}

export function formatDateRange(startIso, endIso, locale = 'de') {
  if (!startIso || !endIso) return '—'
  try {
    const start = formatDateTime(startIso, locale)
    const end = formatDateTime(endIso, locale)
    return `${start} – ${end}`
  } catch {
    return '—'
  }
}
