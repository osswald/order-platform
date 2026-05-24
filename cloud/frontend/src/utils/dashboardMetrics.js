/** Event status labels (aligned with cloud/backend/app/event_status.py). */
export const EVENT_STATUS_LABELS = {
  config: 'Konfiguration',
  test: 'Testbetrieb',
  prod: 'Produktivbetrieb',
  archive: 'Archiviert',
}

export function statusLabel(status) {
  const key = String(status || '').toLowerCase()
  return EVENT_STATUS_LABELS[key] || status || '—'
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
  const t = now.getTime()
  return (events || []).filter((event) => {
    const status = String(event.status || '').toLowerCase()
    if (status !== 'test' && status !== 'prod') return false
    const start = event.start ? new Date(event.start).getTime() : NaN
    const end = event.end ? new Date(event.end).getTime() : NaN
    return !Number.isNaN(start) && !Number.isNaN(end) && start <= t && t <= end
  })
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
        message: `„${event.name}" startet bald und ist noch in Konfiguration.`,
      })
    }

    if ((status === 'test' || status === 'prod') && event.payment_types?.includes('twint') && !event.has_twint_qr) {
      items.push({
        type: 'missing_twint_qr',
        event_id: event.id,
        event_name: event.name,
        message: `„${event.name}": TWINT aktiv, aber kein QR-Code hinterlegt.`,
      })
    }
  }

  return items
}

export function formatEventDateRange(startIso, endIso) {
  if (!startIso || !endIso) return '—'
  try {
    const opts = { dateStyle: 'short', timeStyle: 'short' }
    const start = new Date(startIso).toLocaleString('de-CH', opts)
    const end = new Date(endIso).toLocaleString('de-CH', opts)
    return `${start} – ${end}`
  } catch {
    return '—'
  }
}

export function eventsStatDetail(statusCounts, runningCount) {
  const active = (statusCounts?.test || 0) + (statusCounts?.prod || 0)
  const config = statusCounts?.config || 0
  const parts = []
  if (runningCount > 0) parts.push(`${runningCount} läuft jetzt`)
  if (active > 0) parts.push(`${active} aktiv`)
  if (config > 0) parts.push(`${config} in Konfiguration`)
  return parts.length ? parts.join(' · ') : 'Keine Veranstaltungen'
}
