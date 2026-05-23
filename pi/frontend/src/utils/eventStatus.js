export const STATUS_LABELS = {
  config: 'Konfiguration',
  test: 'Testbetrieb',
  prod: 'Produktivbetrieb',
  archive: 'Archiviert',
}

export function eventStatusLabel(status) {
  const key = String(status || '').toLowerCase()
  return STATUS_LABELS[key] || key || '—'
}
