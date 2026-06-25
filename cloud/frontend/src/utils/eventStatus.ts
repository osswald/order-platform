export const EVENT_STATUS_ORDER = ['config', 'test', 'prod', 'archive'] as const

export type EventStatusKey = (typeof EVENT_STATUS_ORDER)[number]

const STATUS_COLORS: Record<EventStatusKey, string | undefined> = {
  config: undefined,
  test: 'info',
  prod: 'success',
  archive: 'warning',
}

export function eventStatusColor(status: string | null | undefined): string | undefined {
  const key = String(status || '').toLowerCase()
  if (key in STATUS_COLORS) {
    return STATUS_COLORS[key as EventStatusKey]
  }
  return undefined
}

export function eventStatusIndex(status: string | null | undefined): number {
  const key = String(status || '').toLowerCase()
  return EVENT_STATUS_ORDER.indexOf(key as EventStatusKey)
}
