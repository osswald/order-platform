import { computed, onUnmounted, ref, watch } from 'vue'
import { api } from '@/api'
import { useAdminOperations } from '@/composables/useAdminOperations'
import { useBundle } from '@/composables/useBundle'
import { getErrorMessage } from '@/types/api'
import { isEventTest } from '@/utils/eventStatus'

export type LoadTestState = 'idle' | 'running' | 'stopping' | 'done' | 'failed'

export interface LoadTestStatus {
  state: LoadTestState
  event_id?: number | null
  config?: {
    waiter_count?: number
    cash_register_count?: number
    table_min?: number
    table_max?: number
    total_orders?: number
    actors_per_burst?: number
  } | null
  placed?: number
  failed?: number
  receipts_printed?: number
  current_burst?: number
  total_bursts?: number
  last_error?: string | null
  started_at?: string | null
  finished_at?: string | null
}

const status = ref<LoadTestStatus>({ state: 'idle' })
const actionBusy = ref(false)
let pollTimer: ReturnType<typeof setInterval> | null = null

export function useLoadTest() {
  const { opsEvent, opsEventId, cashRegisters, busy } = useAdminOperations()
  const { showToast } = useBundle()

  const isTestEvent = computed(() => isEventTest(opsEvent.value?.status))

  const eventWaiters = computed(() => {
    const cfg = opsEvent.value?.configuration
    const list = cfg?.event_waiters || cfg?.waiters || []
    return list.filter((w) => String(w?.uuid || '').trim())
  })

  const maxWaiters = computed(() => eventWaiters.value.length)
  const maxRegisters = computed(() => cashRegisters.value.length)

  const waiterCount = ref(1)
  const cashRegisterCount = ref(0)
  const tableMin = ref(1)
  const tableMax = ref(40)
  const totalOrders = ref(60)

  watch(
    maxWaiters,
    (max) => {
      if (waiterCount.value > max) waiterCount.value = max
      if (max > 0 && waiterCount.value === 0 && cashRegisterCount.value === 0) {
        waiterCount.value = Math.min(1, max)
      }
    },
    { immediate: true },
  )

  watch(
    maxRegisters,
    (max) => {
      if (cashRegisterCount.value > max) cashRegisterCount.value = max
    },
    { immediate: true },
  )

  const actorsPerBurst = computed(
    () => Math.max(0, waiterCount.value) + Math.max(0, cashRegisterCount.value),
  )

  const estimatedMinutes = computed(() => {
    const actors = actorsPerBurst.value
    if (actors <= 0 || totalOrders.value <= 0) return 0
    return Math.ceil(totalOrders.value / actors)
  })

  const running = computed(
    () => status.value.state === 'running' || status.value.state === 'stopping',
  )

  function stopPolling() {
    if (pollTimer != null) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  function startPolling() {
    stopPolling()
    pollTimer = setInterval(() => {
      void refreshStatus()
    }, 1000)
  }

  async function refreshStatus() {
    try {
      const data = await api<LoadTestStatus>('/v1/load-test/status')
      status.value = data
      if (data.state !== 'running' && data.state !== 'stopping') {
        stopPolling()
      }
    } catch {
      /* ignore transient poll errors */
    }
  }

  async function startLoadTest() {
    if (opsEventId.value == null || !isTestEvent.value) return
    if (actorsPerBurst.value <= 0) {
      showToast('Mindestens ein Kellner oder eine Kasse nötig.', 'err')
      return
    }
    actionBusy.value = true
    try {
      const data = await api<LoadTestStatus>('/v1/load-test/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_id: opsEventId.value,
          waiter_count: waiterCount.value,
          cash_register_count: cashRegisterCount.value,
          table_min: tableMin.value,
          table_max: tableMax.value,
          total_orders: totalOrders.value,
        }),
      })
      status.value = data
      startPolling()
      showToast('Lasttest gestartet.', 'ok')
    } catch (error: unknown) {
      showToast(getErrorMessage(error, 'Lasttest konnte nicht starten.'), 'err')
    } finally {
      actionBusy.value = false
    }
  }

  async function stopLoadTest() {
    actionBusy.value = true
    try {
      const data = await api<LoadTestStatus>('/v1/load-test/stop', { method: 'POST' })
      status.value = data
      startPolling()
      showToast('Stopp angefordert.', 'ok')
    } catch (error: unknown) {
      showToast(getErrorMessage(error, 'Stopp fehlgeschlagen.'), 'err')
    } finally {
      actionBusy.value = false
    }
  }

  onUnmounted(() => {
    stopPolling()
  })

  // Resume polling if we land on the page while a job is already running
  void refreshStatus().then(() => {
    if (status.value.state === 'running' || status.value.state === 'stopping') {
      startPolling()
    }
  })

  return {
    busy,
    actionBusy,
    status,
    running,
    isTestEvent,
    maxWaiters,
    maxRegisters,
    waiterCount,
    cashRegisterCount,
    tableMin,
    tableMax,
    totalOrders,
    actorsPerBurst,
    estimatedMinutes,
    startLoadTest,
    stopLoadTest,
    refreshStatus,
  }
}
