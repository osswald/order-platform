import { apiFetch } from '../api'
import { parseApiErrorDetail } from './apiError'

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
  return endDateFromStartAndDuration(start, 7)
}

export function formatDeDate(isoOrDate) {
  if (!isoOrDate) return '—'
  const d = isoOrDate instanceof Date ? isoOrDate : new Date(isoOrDate)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString('de-DE')
}

export function lendingRangeHint(start, end) {
  const days = inclusiveDurationDays(start, end)
  if (!days) return ''
  return `${days} Tag${days === 1 ? '' : 'e'} (${formatDeDate(start)} – ${formatDeDate(end)})`
}

export const APPLIANCE_TYPE_LABELS = {
  server: 'Server',
  printer: 'Drucker',
  mobile: 'Mobil',
  tablet: 'Tablet',
  router: 'Router',
  ap: 'Access Point',
}

export function applianceTypeLabel(type) {
  return APPLIANCE_TYPE_LABELS[type] || type
}

export function applianceDisplayName(appliance) {
  if (appliance?.name) return appliance.name
  return `#${appliance?.id ?? '?'}`
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
