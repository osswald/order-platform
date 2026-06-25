import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api'
import { useBundle } from '@/composables/useBundle'
import { assignKitchenMonitorSlugs } from '@/utils/kitchenMonitorSlug'
import type {
  EdgeBundleEvent,
  PrinterTestStationPrintsResponse,
  StationTestPrintResult,
} from '@/types/api'
import { getErrorMessage } from '@/types/api'

const opsEventId = ref<number | null>(null)
const opsRegisterUuid = ref<string | null>(null)
const testPrintBusy = ref(false)

export function useAdminOperations() {
  const router = useRouter()
  const { bundle, busy, showToast, selectedEventId } = useBundle()

  const events = computed(() => bundle.value?.events || [])
  const showEventSelect = computed(() => events.value.length > 1)
  const singleEventName = computed(() => {
    if (events.value.length !== 1) return ''
    return events.value[0]?.name || ''
  })

  const opsEvent = computed(
    () => events.value.find((e) => Number(e.id) === Number(opsEventId.value)) || null,
  )

  const cashRegisters = computed(() => {
    const regs = opsEvent.value?.configuration?.cash_registers || []
    return regs
      .slice()
      .sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'de'))
  })

  const showRegisterSelect = computed(() => cashRegisters.value.length > 1)
  const singleRegisterName = computed(() => {
    if (cashRegisters.value.length !== 1) return ''
    return cashRegisters.value[0]?.name || ''
  })

  const hasKitchenMonitor = computed(() => Boolean(opsEvent.value?.kitchen_monitors_enabled))
  const hasCashRegisters = computed(() => cashRegisters.value.length > 0)

  const kitchenMonitorRows = computed(() => {
    const ev = opsEvent.value
    if (!ev?.kitchen_monitors_enabled) return []
    const printers = (ev.configuration?.kitchen_monitors || [])
      .map((row) => ({
        printer_appliance_id: Number(row.printer_appliance_id),
        label: String(row.label || `Drucker #${row.printer_appliance_id}`),
        sort_order: Number(row.sort_order) || 0,
      }))
      .filter((row) => Number.isFinite(row.printer_appliance_id))
      .sort((a, b) => a.sort_order - b.sort_order || a.label.localeCompare(b.label, 'de'))
    const slugs = assignKitchenMonitorSlugs(printers)
    return printers.map((printer) => {
      const slug = slugs.get(printer.printer_appliance_id) || 'station'
      return {
        printerId: printer.printer_appliance_id,
        label: printer.label,
        slug,
        url: kitchenUrlForSlug(slug),
      }
    })
  })

  const displayUrl = computed(() => {
    if (!opsRegisterUuid.value) return ''
    const path = router.resolve({
      name: 'register-display',
      params: { registerUuid: opsRegisterUuid.value },
    }).href
    if (typeof window === 'undefined') return path
    return `${window.location.origin}${path}`
  })

  function kitchenUrlForSlug(slug: string) {
    const path = router.resolve({
      name: 'kitchen',
      params: { printerSlug: slug },
    }).href
    if (typeof window === 'undefined') return path
    return `${window.location.origin}${path}`
  }

  watch(events, (list: EdgeBundleEvent[]) => {
    if (!list.length) {
      opsEventId.value = null
      opsRegisterUuid.value = null
      return
    }
    if (opsEventId.value == null || !list.some((e) => Number(e.id) === Number(opsEventId.value))) {
      opsEventId.value = selectedEventId.value ?? list[0].id
    }
  }, { immediate: true })

  watch(cashRegisters, (regs) => {
    if (!regs.length) {
      opsRegisterUuid.value = null
      return
    }
    if (opsRegisterUuid.value == null || !regs.some((r) => String(r.uuid) === opsRegisterUuid.value)) {
      opsRegisterUuid.value = String(regs[0].uuid)
    }
  }, { immediate: true })

  async function doTestPrint() {
    if (opsEventId.value == null) return
    testPrintBusy.value = true
    try {
      const data = await api<PrinterTestStationPrintsResponse>('/v1/printers/test-station-prints', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event_id: opsEventId.value }),
      })
      const printed = data.printed ?? 0
      const failed = data.failed ?? 0
      const total = (data.results || []).length
      if (failed === 0) {
        showToast(`Testdruck: ${printed}/${total} Stationen OK.`, 'ok')
      } else {
        const firstErr = (data.results || []).find((r: StationTestPrintResult) => !r.ok)?.error
        showToast(
          `Testdruck: ${printed}/${total} OK, ${failed} Fehler.${firstErr ? ` ${firstErr}` : ''}`,
          'err',
        )
      }
    } catch (error: unknown) {
      showToast(getErrorMessage(error, 'Testdruck fehlgeschlagen.'), 'err')
    } finally {
      testPrintBusy.value = false
    }
  }

  function openKitchen(slug: string) {
    selectedEventId.value = opsEventId.value
    const url = kitchenUrlForSlug(slug)
    window.open(url, '_blank', 'noopener,noreferrer')
  }

  async function copyKitchenUrl(url: string) {
    if (!url) return
    try {
      await navigator.clipboard.writeText(url)
      showToast('URL kopiert.', 'ok')
    } catch {
      showToast(url, 'ok')
    }
  }

  function openPickup() {
    selectedEventId.value = opsEventId.value
    router.push({ name: 'pickup' })
  }

  async function copyDisplayUrl() {
    const url = displayUrl.value
    if (!url) return
    try {
      await navigator.clipboard.writeText(url)
      showToast('URL kopiert.', 'ok')
    } catch {
      showToast(url, 'ok')
    }
  }

  function openDisplay() {
    const url = displayUrl.value
    if (!url) return
    selectedEventId.value = opsEventId.value
    window.open(url, '_blank', 'noopener,noreferrer')
  }

  return {
    bundle,
    busy,
    opsEventId,
    opsRegisterUuid,
    events,
    showEventSelect,
    singleEventName,
    opsEvent,
    cashRegisters,
    showRegisterSelect,
    singleRegisterName,
    hasKitchenMonitor,
    hasCashRegisters,
    kitchenMonitorRows,
    displayUrl,
    testPrintBusy,
    doTestPrint,
    openKitchen,
    copyKitchenUrl,
    openPickup,
    copyDisplayUrl,
    openDisplay,
  }
}
