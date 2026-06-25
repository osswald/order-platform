import type { KitchenOrderTicket } from '@/types/api'

export const KITCHEN_URGENCY_GREEN_MS = 5 * 60 * 1000
export const KITCHEN_URGENCY_AMBER_MS = 10 * 60 * 1000

export type KitchenUrgencyLevel = 'green' | 'amber' | 'red'

export function ticketOrderedAtMs(ticket: KitchenOrderTicket): number {
  const raw = ticket.ordered_at || ticket.created_at
  const parsed = Date.parse(String(raw || ''))
  return Number.isFinite(parsed) ? parsed : 0
}

export function sortTicketsByWaitTime(tickets: KitchenOrderTicket[]): KitchenOrderTicket[] {
  return [...tickets].sort((a, b) => {
    const diff = ticketOrderedAtMs(a) - ticketOrderedAtMs(b)
    if (diff !== 0) return diff
    return Number(a.id) - Number(b.id)
  })
}

export function ticketElapsedMs(ticket: KitchenOrderTicket, nowMs = Date.now()): number {
  const orderedAt = ticketOrderedAtMs(ticket)
  if (!orderedAt) return 0
  return Math.max(0, nowMs - orderedAt)
}

export function ticketUrgencyLevel(ticket: KitchenOrderTicket, nowMs = Date.now()): KitchenUrgencyLevel {
  const elapsed = ticketElapsedMs(ticket, nowMs)
  if (elapsed >= KITCHEN_URGENCY_AMBER_MS) return 'red'
  if (elapsed >= KITCHEN_URGENCY_GREEN_MS) return 'amber'
  return 'green'
}

export function formatElapsedMinutes(ms: number): string {
  const minutes = Math.max(0, Math.floor(ms / 60000))
  if (minutes < 60) return `${minutes} min`
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return rest > 0 ? `${hours}h ${rest}m` : `${hours}h`
}

export const KITCHEN_MIN_COLUMN_WIDTH_PX = 260
export const KITCHEN_ORDER_GAP_PX = 8

export function computeKitchenColumnLayout(
  containerWidth: number,
  options: { minColumnWidth?: number; gapPx?: number } = {},
): { columnCount: number; columnWidthPx: number } {
  const minColumnWidth = options.minColumnWidth ?? KITCHEN_MIN_COLUMN_WIDTH_PX
  const gapPx = options.gapPx ?? KITCHEN_ORDER_GAP_PX
  if (containerWidth <= 0) {
    return { columnCount: 1, columnWidthPx: minColumnWidth }
  }
  const columnCount = Math.max(1, Math.floor((containerWidth + gapPx) / (minColumnWidth + gapPx)))
  const columnWidthPx = (containerWidth - (columnCount - 1) * gapPx) / columnCount
  return { columnCount, columnWidthPx }
}

export function ticketStatusLabel(status: string | null | undefined): string {
  switch (String(status || '').toLowerCase()) {
    case 'partial':
      return 'Teilweise'
    case 'done':
      return 'Fertig'
    default:
      return 'Neu'
  }
}

interface KitchenLineAdditionInput {
  article_id: number
  qty?: number | null
  name?: string | null
}

interface KitchenLineWithAdditions {
  additions?: KitchenLineAdditionInput[] | null
}

interface KitchenArticleLookup {
  name?: string | null
}

export function kitchenLineAdditionLabels(
  line: KitchenLineWithAdditions,
  articles: Record<string, KitchenArticleLookup> | null | undefined,
): string[] {
  const additions = line.additions || []
  if (!additions.length) return []
  return additions.map((add) => {
    const id = Number(add.article_id)
    const article = articles?.[String(id)] || articles?.[id as unknown as string]
    const name = add.name || article?.name || `#${id}`
    return `+ ${Math.max(1, Number(add.qty) || 1)}x ${name}`
  })
}
