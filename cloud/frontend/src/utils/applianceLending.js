import { apiFetch } from '../api'
import { i18n } from '../i18n'
import { formatDate } from './localeFormat'
import { parseApiErrorDetail } from './apiError'

function t(key, params) {
  return i18n.global.t(key, params)
}

/** Local calendar date at midnight (for Vuetify date pickers). */
export function toLocalCalendarDate(d) {
  if (!d) return null
  const x = d instanceof Date ? d : new Date(d)
  if (Number.isNaN(x.getTime())) return null
  return new Date(x.getFullYear(), x.getMonth(), x.getDate())
}

export function toIsoDate(d) {
  if (!d) return null
  const x = d instanceof Date ? d : new Date(d)
  const y = x.getFullYear()
  const mo = String(x.getMonth() + 1).padStart(2, '0')
  const day = String(x.getDate()).padStart(2, '0')
  return `${y}-${mo}-${day}`
}

function toUtcMidnight(d) {
  const x = d instanceof Date ? d : new Date(d)
  return Date.UTC(x.getFullYear(), x.getMonth(), x.getDate())
}

/** Inclusive calendar days between start and end (same rule as cloud backend). */
export function inclusiveDurationDays(start, end) {
  if (!start || !end) return null
  const days = Math.floor((toUtcMidnight(end) - toUtcMidnight(start)) / 86400000) + 1
  return days >= 1 ? days : null
}

export function endDateFromStartAndDuration(start, durationDays) {
  if (!start || durationDays == null || durationDays < 1) return null
  const x = start instanceof Date ? new Date(start) : new Date(start)
  const end = new Date(x)
  end.setDate(end.getDate() + durationDays - 1)
  return end
}

export function isValidLendingRange(start, end) {
  if (!start || !end) return false
  return toUtcMidnight(end) >= toUtcMidnight(start)
}

export function defaultLendingEndDate(start = new Date()) {
  const base = toLocalCalendarDate(start) ?? new Date()
  return endDateFromStartAndDuration(base, 7)
}

export function formatDeDate(isoOrDate) {
  return formatDate(isoOrDate, i18n.global.locale.value)
}

export function lendingRangeHint(start, end) {
  const days = inclusiveDurationDays(start, end)
  if (!days) return ''
  const dayLabel = days === 1 ? t('lending.day') : t('lending.days')
  return t('lending.rangeHint', {
    days,
    dayLabel,
    start: formatDeDate(start),
    end: formatDeDate(end),
  })
}

export { applianceTypeLabel } from './applianceType'

export function applianceDisplayName(appliance) {
  const base = appliance?.name ? appliance.name : `#${appliance?.id ?? '?'}`
  if (appliance?.type === 'printer') {
    const ip = appliance.ip_address?.trim() || '—'
    return `${base} (${ip})`
  }
  return base
}

export async function cancelPlannedLending(organisationId, lendingId) {
  const response = await apiFetch(
    `/organisations/${organisationId}/appliance-lendings/${lendingId}`,
    { method: 'DELETE' },
  )
  if (!response.ok) {
    throw new Error(await parseApiErrorDetail(response))
  }
}

export async function cancelPlannedLendingForAppliance(applianceId, lendingId) {
  const response = await apiFetch(`/appliances/${applianceId}/lendings/${lendingId}`, {
    method: 'DELETE',
  })
  if (!response.ok) {
    throw new Error(await parseApiErrorDetail(response))
  }
}
