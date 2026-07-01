const ZURICH_TZ = 'Europe/Zurich'

const decimalFormat = {
  style: 'decimal',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
} as const

const percentFormat = {
  style: 'decimal',
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
} as const

const datetimeShort = {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
  timeZone: ZURICH_TZ,
} as const

const dateOnly = {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  timeZone: ZURICH_TZ,
} as const

const timeOnly = {
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
  timeZone: ZURICH_TZ,
} as const

/** Bucket chart labels: dd.MM. HH:mm (date + time, no year). */
const bucketLabel = {
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
  timeZone: ZURICH_TZ,
} as const

const formatLocaleKeys = ['de-CH', 'en-CH', 'de-DE', 'en-DE'] as const

export const numberFormats = Object.fromEntries(
  formatLocaleKeys.map((locale) => [
    locale,
    {
      decimal: decimalFormat,
      percent: percentFormat,
    },
  ]),
)

export const datetimeFormats = Object.fromEntries(
  formatLocaleKeys.map((locale) => [
    locale,
    {
      short: datetimeShort,
      date: dateOnly,
      time: timeOnly,
      bucket: bucketLabel,
    },
  ]),
)
