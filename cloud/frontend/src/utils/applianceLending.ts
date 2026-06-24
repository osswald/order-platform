import { apiJson } from '@/api'
import { i18n } from '@/i18n'
import { formatDate } from './localeFormat'
import type { ApplianceRead } from '@/types/api'

function t(key: string, params?: Record<string, unknown>): string {
  return i18n.global.t(key, params ?? {})
}

/** Local calendar date at midnight (for Vuetify date pickers). */
export function toLocalCalendarDate(d: string | Date | null | undefined): Date | null {
  if (!d) return null
  const x = d instanceof Date ? d : new Date(d)
  if (Number.isNaN(x.getTime())) return null
  return new Date(x.getFullYear(), x.getMonth(), x.getDate())
}

export function toIsoDate(d: string | Date | null | undefined): string | null {
  if (!d) return null
  const x = d instanceof Date ? d : new Date(d)
  const y = x.getFullYear()
  const mo = String(x.getMonth() + 1).padStart(2, '0')
  const day = String(x.getDate()).padStart(2, '0')
  return `${y}-${mo}-${day}`
}

function toUtcMidnight(d: string | Date): number {
  const x = d instanceof Date ? d : new Date(d)
  return Date.UTC(x.getFullYear(), x.getMonth(), x.getDate())
}

/** Inclusive calendar days between start and end (same rule as cloud backend). */
export function inclusiveDurationDays(
  start: string | Date | null | undefined,
  end: string | Date | null | undefined,
): number | null {
  if (!start || !end) return null
  const days = Math.floor((toUtcMidnight(end) - toUtcMidnight(start)) / 86400000) + 1
  return days >= 1 ? days : null
}

export function endDateFromStartAndDuration(
  start: string | Date | null | undefined,
  durationDays: number | null | undefined,
): Date | null {
  if (!start || durationDays == null || durationDays < 1) return null
  const x = start instanceof Date ? new Date(start) : new Date(start)
  const end = new Date(x)
  end.setDate(end.getDate() + durationDays - 1)
  return end
}

export function isValidLendingRange(
  start: string | Date | null | undefined,
  end: string | Date | null | undefined,
): boolean {
  if (!start || !end) return false
  return toUtcMidnight(end) >= toUtcMidnight(start)
}

export function defaultLendingEndDate(start: string | Date = new Date()): Date | null {
  const base = toLocalCalendarDate(start) ?? new Date()
  return endDateFromStartAndDuration(base, 7)
}

export function formatDeDate(isoOrDate: string | Date | null | undefined): string {
  return formatDate(isoOrDate, i18n.global.locale.value)
}

export function lendingRangeHint(
  start: string | Date | null | undefined,
  end: string | Date | null | undefined,
): string {
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

export function applianceDisplayName(appliance: Pick<ApplianceRead, 'id' | 'name' | 'type' | 'ip_address'>): string {
  const base = appliance?.name ? appliance.name : `#${appliance?.id ?? '?'}`
  if (appliance?.type === 'printer') {
    const ip = appliance.ip_address?.trim() || '—'
    return `${base} (${ip})`
  }
  return base
}

export async function cancelPlannedLending(organisationId: number, lendingId: number): Promise<void> {
  await apiJson(`/organisations/${organisationId}/appliance-lendings/${lendingId}`, {
    method: 'DELETE',
  })
}

export async function cancelPlannedLendingForAppliance(applianceId: number, lendingId: number): Promise<void> {
  await apiJson(`/appliances/${applianceId}/lendings/${lendingId}`, {
    method: 'DELETE',
  })
}
