import { i18n } from '../i18n'
import { formatDateRange } from './localeFormat'

function t(key, params) {
  return i18n.global.t(key, params)
}

export function statusLabel(status) {
  const key = String(status || '').toLowerCase()
  const labelKey = `eventStatus.${key}`
  const translated = t(labelKey)
  if (translated !== labelKey) return translated
  return status || t('common.emDash')
}

export function eventsByStatus(events) {
  const counts = { config: 0, test: 0, prod: 0, archive: 0 }
  for (const event of events || []) {
    const key = String(event.status || 'config').toLowerCase()
    if (key in counts) counts[key] += 1
  }
  return counts
}

export function runningEvents(events, now = new Date()) {
  const tMs = now.getTime()
  return (events || []).filter((event) => {
    const status = String(event.status || '').toLowerCase()
    if (status !== 'test' && status !== 'prod') return false
    const start = event.start ? new Date(event.start).getTime() : NaN
    const end = event.end ? new Date(event.end).getTime() : NaN
    return !Number.isNaN(start) && !Number.isNaN(end) && start <= tMs && tMs <= end
  })
}

export function attentionMessage(item) {
  if (!item?.type) return ''
  return t(`dashboard.attentionMessages.${item.type}`, { name: item.event_name ?? '' })
}

/**
 * Client-side attention hints (server summary is authoritative when loaded).
 */
export function attentionItems(events, now = new Date()) {
  const horizon = now.getTime() + 7 * 24 * 60 * 60 * 1000
  const items = []

  for (const event of events || []) {
    const status = String(event.status || '').toLowerCase()
    const start = event.start ? new Date(event.start).getTime() : null

    if (status === 'config' && start != null && start <= horizon) {
      items.push({
        type: 'config_starting_soon',
        event_id: event.id,
        event_name: event.name,
      })
    }

    if ((status === 'test' || status === 'prod') && event.payment_types?.includes('twint') && !event.has_twint_qr) {
      items.push({
        type: 'missing_twint_qr',
        event_id: event.id,
        event_name: event.name,
      })
    }
  }

  return items
}

export function formatEventDateRange(startIso, endIso) {
  return formatDateRange(startIso, endIso, i18n.global.locale.value)
}

export function eventsStatDetail(statusCounts, runningCount) {
  const active = (statusCounts?.test || 0) + (statusCounts?.prod || 0)
  const config = statusCounts?.config || 0
  const parts = []
  if (runningCount > 0) parts.push(t('dashboard.eventsDetail.runningNow', { count: runningCount }))
  if (active > 0) parts.push(t('dashboard.eventsDetail.active', { count: active }))
  if (config > 0) parts.push(t('dashboard.eventsDetail.inConfig', { count: config }))
  return parts.length ? parts.join(' · ') : t('dashboard.noEvents')
}
