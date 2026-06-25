import type { KitchenTicketLineEntry } from '@/types/api'

export function cycleLineSelection(
  line: KitchenTicketLineEntry,
  currentSelected: number,
): number {
  const max = Math.max(0, Number(line.qty_remaining) || 0)
  if (max <= 0) return 0
  const next = currentSelected + 1
  return next > max ? 0 : next
}

export function lineSelectionLabel(
  line: KitchenTicketLineEntry,
  selectedQty: number,
  articleName: string,
): string {
  const remaining = Math.max(0, Number(line.qty_remaining) || 0)
  if (selectedQty > 0) {
    return `${selectedQty}/${remaining} ${articleName}`
  }
  return `${remaining} ${articleName}`
}

export function hasTicketSelection(
  ticketLineIds: number[],
  selectedByLineId: Record<number, number>,
): boolean {
  return ticketLineIds.some((id) => (selectedByLineId[id] || 0) > 0)
}

export function selectionPayloadForTicket(
  lines: KitchenTicketLineEntry[],
  selectedByLineId: Record<number, number>,
): Array<{ line_id: number; qty: number }> {
  return lines
    .map((line) => ({
      line_id: line.id,
      qty: Math.min(
        Math.max(0, selectedByLineId[line.id] || 0),
        Math.max(0, Number(line.qty_remaining) || 0),
      ),
    }))
    .filter((row) => row.qty > 0)
}

export function capSelectionToLines(
  selectedByLineId: Record<number, number>,
  lines: KitchenTicketLineEntry[],
): Record<number, number> {
  const out: Record<number, number> = { ...selectedByLineId }
  for (const line of lines) {
    const cap = Math.max(0, Number(line.qty_remaining) || 0)
    const current = out[line.id] || 0
    if (current > cap) out[line.id] = cap
    if (cap <= 0) delete out[line.id]
  }
  return out
}
