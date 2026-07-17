import { computed, ref } from 'vue'
import type { KitchenOrderTicket, KitchenTicketLineEntry } from '@/types/api'
import {
  capSelectionToLines,
  cycleLineSelection,
  hasTicketSelection,
  selectionPayloadForTicket,
} from '@/utils/kitchenLineSelection'

export function useKitchenLineSelection() {
  const selectedByLineId = ref<Record<number, number>>({})

  function selectedQty(lineId: number): number {
    return selectedByLineId.value[lineId] || 0
  }

  function cycleLine(line: KitchenTicketLineEntry) {
    const next = cycleLineSelection(line, selectedQty(line.id))
    const copy = { ...selectedByLineId.value }
    if (next > 0) copy[line.id] = next
    else delete copy[line.id]
    selectedByLineId.value = copy
  }

  function clearTicket(ticket: KitchenOrderTicket) {
    const copy = { ...selectedByLineId.value }
    for (const line of ticket.lines || []) {
      delete copy[line.id]
    }
    selectedByLineId.value = copy
  }

  function reconcileLines(lines: KitchenTicketLineEntry[]) {
    selectedByLineId.value = capSelectionToLines(selectedByLineId.value, lines)
  }

  const hasSelectionForTicket = (ticket: KitchenOrderTicket) =>
    computed(() => hasTicketSelection((ticket.lines || []).map((line) => line.id), selectedByLineId.value))

  function payloadForTicket(ticket: KitchenOrderTicket) {
    return selectionPayloadForTicket(ticket.lines || [], selectedByLineId.value)
  }

  return {
    selectedByLineId,
    selectedQty,
    cycleLine,
    clearTicket,
    reconcileLines,
    hasSelectionForTicket,
    payloadForTicket,
  }
}
