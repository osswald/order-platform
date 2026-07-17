import { computed, ref, watch, type Ref } from 'vue'
import { api } from '@/api'
import type {
  EdgeBundleEvent,
  KitchenOrderTicket,
  KitchenOrdersResponse,
  KitchenTicketPrintResponse,
} from '@/types/api'
import { getErrorMessage } from '@/types/api'
import { kitchenMonitorPrinterBySlug } from '@/utils/kitchenMonitorSlug'
import { sortTicketsByWaitTime } from '@/utils/kitchenMonitorHelpers'

interface KitchenPrinterTab {
  printer_appliance_id: number
  label: string
  sort_order: number
}

interface UseKitchenMonitorOptions {
  event: Ref<EdgeBundleEvent | null | undefined>
  printerSlug: Ref<string | undefined>
}

export function useKitchenMonitor({ event, printerSlug }: UseKitchenMonitorOptions) {
  const selectedPrinterId = ref<number | null>(null)
  const orders = ref<KitchenOrderTicket[]>([])
  const loading = ref(false)
  const error = ref('')
  const busyTicketId = ref<number | null>(null)
  let pollTimer: ReturnType<typeof setInterval> | null = null

  const kitchenPrinters = computed((): KitchenPrinterTab[] => {
    const ev = event.value
    if (!ev?.kitchen_monitors_enabled) return []
    const rows = ev?.configuration?.kitchen_monitors || []
    return rows
      .map((row) => ({
        printer_appliance_id: Number(row.printer_appliance_id),
        label: String(row.label || `Drucker #${row.printer_appliance_id}`),
        sort_order: Number(row.sort_order) || 0,
      }))
      .filter((row) => Number.isFinite(row.printer_appliance_id))
      .sort((a, b) => a.sort_order - b.sort_order || a.label.localeCompare(b.label))
  })

  const selectedPrinter = computed(() => {
    if (selectedPrinterId.value == null) return null
    return kitchenPrinters.value.find((row) => row.printer_appliance_id === selectedPrinterId.value) || null
  })

  const unknownPrinterSlug = computed(() => {
    const slug = String(printerSlug.value || '').trim()
    if (!slug || !kitchenPrinters.value.length) return false
    return !kitchenMonitorPrinterBySlug(slug, kitchenPrinters.value)
  })

  function resolvePrinterFromSlug() {
    const printers = kitchenPrinters.value
    const slug = String(printerSlug.value || '').trim()
    if (!printers.length || !slug) {
      selectedPrinterId.value = null
      return
    }
    const match = kitchenMonitorPrinterBySlug(slug, printers)
    selectedPrinterId.value = match?.printer_appliance_id ?? null
  }

  async function loadOrders() {
    const ev = event.value
    const printerId = selectedPrinterId.value
    if (!ev?.id || printerId == null) {
      orders.value = []
      return
    }
    loading.value = true
    error.value = ''
    try {
      const data = await api<KitchenOrdersResponse>(
        `/v1/kitchen/orders?event_id=${encodeURIComponent(ev.id)}&printer_appliance_id=${encodeURIComponent(printerId)}`,
      )
      orders.value = sortTicketsByWaitTime(data?.orders || [])
    } catch (e: unknown) {
      error.value = getErrorMessage(e, 'Küchenmonitor konnte nicht geladen werden.')
    } finally {
      loading.value = false
    }
  }

  async function printComplete(ticket: KitchenOrderTicket) {
    if (busyTicketId.value) return
    busyTicketId.value = ticket.id
    error.value = ''
    try {
      await api<KitchenTicketPrintResponse>(`/v1/kitchen/tickets/${ticket.id}/print`, { method: 'POST' })
      await loadOrders()
    } catch (e: unknown) {
      error.value = getErrorMessage(e, 'Drucken fehlgeschlagen.')
    } finally {
      busyTicketId.value = null
    }
  }

  async function printPartial(
    ticket: KitchenOrderTicket,
    lines: Array<{ line_id: number; qty: number }>,
  ) {
    if (busyTicketId.value || !lines.length) return
    busyTicketId.value = ticket.id
    error.value = ''
    try {
      await api<KitchenTicketPrintResponse>(`/v1/kitchen/tickets/${ticket.id}/print-partial`, {
        method: 'POST',
        body: JSON.stringify({ lines }),
      })
      await loadOrders()
    } catch (e: unknown) {
      error.value = getErrorMessage(e, 'Teildruck fehlgeschlagen.')
    } finally {
      busyTicketId.value = null
    }
  }

  function stopPolling() {
    if (pollTimer) clearInterval(pollTimer)
    pollTimer = null
  }

  function startPolling() {
    if (pollTimer) clearInterval(pollTimer)
    pollTimer = setInterval(() => {
      if (document.visibilityState === 'visible' && !busyTicketId.value) {
        void loadOrders()
      }
    }, 5000)
  }

  watch([kitchenPrinters, printerSlug], resolvePrinterFromSlug, { immediate: true })
  watch(selectedPrinterId, () => {
    void loadOrders()
  })

  return {
    kitchenPrinters,
    selectedPrinterId,
    selectedPrinter,
    unknownPrinterSlug,
    orders,
    loading,
    error,
    busyTicketId,
    loadOrders,
    printComplete,
    printPartial,
    startPolling,
    stopPolling,
  }
}
