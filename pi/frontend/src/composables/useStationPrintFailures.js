import { computed, ref } from 'vue'
import { api } from '../api'

const failedJobs = ref([])
const loadingFailed = ref(false)
const retryingId = ref(null)

const POLL_MS = 1500
const DEFAULT_WATCH_TIMEOUT_MS = 30_000

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function failureLabel(job) {
  const station = job.station_name || job.station_uuid || 'Station'
  const table = job.table_number ? ` (Tisch ${job.table_number})` : ''
  return `Stationsbon «${station}»${table} konnte nicht gedruckt werden.`
}

async function fetchJob(id) {
  return api(`/v1/print-jobs/${id}`)
}

/**
 * Poll print jobs until all sent, any error, or timeout.
 * @param {number[]} ids
 * @param {{ onFailed?: (job: object) => void, timeoutMs?: number }} opts
 */
async function watchJobIds(ids, { onFailed, timeoutMs = DEFAULT_WATCH_TIMEOUT_MS } = {}) {
  const pending = new Set((ids || []).filter((id) => id != null))
  if (!pending.size) return

  const deadline = Date.now() + timeoutMs
  while (pending.size && Date.now() < deadline) {
    await sleep(POLL_MS)
    for (const id of [...pending]) {
      try {
        const job = await fetchJob(id)
        if (job.status === 'sent') {
          pending.delete(id)
        } else if (job.status === 'error') {
          pending.delete(id)
          onFailed?.(job)
        }
      } catch {
        /* keep polling */
      }
    }
  }
}

async function loadFailedJobs({ eventId, waiterUuid }) {
  if (!eventId || !waiterUuid) {
    failedJobs.value = []
    return []
  }
  loadingFailed.value = true
  try {
    const params = new URLSearchParams({
      status: 'error',
      waiter_uuid: waiterUuid,
      event_id: String(eventId),
      kinds: 'station_order,kitchen_ticket',
    })
    const rows = await api(`/v1/print-jobs?${params.toString()}`)
    failedJobs.value = Array.isArray(rows) ? rows : []
    return failedJobs.value
  } catch {
    failedJobs.value = []
    return []
  } finally {
    loadingFailed.value = false
  }
}

async function retryJob(id, { showToast, onFailed } = {}) {
  if (retryingId.value != null) return
  retryingId.value = id
  try {
    await api(`/v1/print-jobs/${id}/retry`, { method: 'POST' })
    showToast?.('Druck erneut an Drucker gesendet.', 'ok')
    await watchJobIds([id], {
      timeoutMs: DEFAULT_WATCH_TIMEOUT_MS,
      onFailed: (job) => {
        onFailed?.(job)
        showToast?.(failureLabel(job), 'err')
      },
    })
    const job = await fetchJob(id)
    if (job.status === 'sent') {
      failedJobs.value = failedJobs.value.filter((j) => j.id !== id)
    } else if (job.status === 'error') {
      const idx = failedJobs.value.findIndex((j) => j.id === id)
      if (idx >= 0) failedJobs.value[idx] = job
      else failedJobs.value = [job, ...failedJobs.value]
    }
    return job
  } catch (e) {
    showToast?.(e.message || 'Erneut drucken fehlgeschlagen.', 'err')
    throw e
  } finally {
    retryingId.value = null
  }
}

let waiterPollTimer = null

export function startWaiterPrintFailurePolling(getContext) {
  stopWaiterPrintFailurePolling()
  const tick = async () => {
    const { eventId, waiterUuid } = getContext()
    if (!eventId || !waiterUuid) {
      failedJobs.value = []
      return
    }
    await loadFailedJobs({ eventId, waiterUuid })
  }
  tick()
  waiterPollTimer = setInterval(tick, 20_000)
}

export function stopWaiterPrintFailurePolling() {
  if (waiterPollTimer) {
    clearInterval(waiterPollTimer)
    waiterPollTimer = null
  }
}

export function useStationPrintFailures() {
  const failedCount = computed(() => failedJobs.value.length)

  return {
    failedJobs,
    failedCount,
    loadingFailed,
    retryingId,
    failureLabel,
    watchJobIds,
    loadFailedJobs,
    retryJob,
    fetchJob,
    startWaiterPrintFailurePolling,
    stopWaiterPrintFailurePolling,
  }
}
