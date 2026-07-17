/** Map vue-i18n UI locale + organisation country to a BCP 47 format locale tag. */

const DEFAULT_COUNTRY_CODE = 'CH'

export function resolveFormatLocale(uiLocale: string, countryCode?: string | null): string {
  const primary = (uiLocale || 'de').split(',')[0].trim().toLowerCase()
  const lang = primary.startsWith('en') ? 'en' : 'de'
  const country = (countryCode || DEFAULT_COUNTRY_CODE).trim().toUpperCase() || DEFAULT_COUNTRY_CODE
  return `${lang}-${country}`
}

/** BCP 47 tag for vue-i18n numberFormats / datetimeFormats keys. */
export function intlLocale(uiLocale: string, countryCode?: string | null): string {
  return resolveFormatLocale(uiLocale, countryCode)
}

export function collatorLocale(uiLocale: string, countryCode?: string | null): string {
  return intlLocale(uiLocale, countryCode)
}
