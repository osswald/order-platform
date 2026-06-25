export const STATUS_LABELS = {
  config: 'Konfiguration',
  test: 'Testbetrieb',
  prod: 'Produktivbetrieb',
  archive: 'Archiviert',
}

export function eventStatusLabel(status: string | null | undefined): string {
  const key = String(status || '').toLowerCase() as keyof typeof STATUS_LABELS
  return STATUS_LABELS[key] || key || '—'
}
