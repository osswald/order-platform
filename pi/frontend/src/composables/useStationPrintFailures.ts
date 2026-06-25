import { computed, ref } from 'vue'
import { api } from '@/api'
import type { PrintJobSummary } from '@/types/api'
import { getErrorMessage } from '@/types/api'
import type { ToastState } from '@/types/cart'

const failedJobs = ref<PrintJobSummary[]>([])
const loadingFailed = ref(false)
const retryingId = ref<number | null>(null)
const deletingId = ref<number | null>(null)

const POLL_MS = 1500
const DEFAULT_WATCH_TIMEOUT_MS = 30_000

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export function failureLabel(job: PrintJobSummary): string {
  const station = job.station_name || job.station_uuid || 'Station'
  const table = job.table_number ? ` (Tisch ${job.table_number})` : ''
  return `Stationsbon «${station}»${table} konnte nicht gedruckt werden.`
}

async function fetchJob(id: number): Promise<PrintJobSummary> {
  return api<PrintJobSummary>(`/v1/print-jobs/${id}`)
}

export interface WatchJobIdsOptions {
  onFailed?: (job: PrintJobSummary) => void
  timeoutMs?: number
}

export async function watchJobIds(
  ids: Array<number | null | undefined>,
  { onFailed, timeoutMs = DEFAULT_WATCH_TIMEOUT_MS }: WatchJobIdsOptions = {},
): Promise<void> {
  const pending = new Set((ids || []).filter((id): id is number => id != null))
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

export interface LoadFailedJobsInput {
  eventId: number
  waiterUuid: string
}

export async function loadFailedJobs({
  eventId,
  waiterUuid,
}: LoadFailedJobsInput): Promise<PrintJobSummary[]> {
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
    const rows = await api<PrintJobSummary[]>(`/v1/print-jobs?${params.toString()}`)
    failedJobs.value = Array.isArray(rows) ? rows : []
    return failedJobs.value
  } catch {
    failedJobs.value = []
    return []
  } finally {
    loadingFailed.value = false
  }
}

type ShowToastFn = (message: string, type?: ToastState['type']) => void

export async function deleteJob(
  id: number,
  { showToast }: { showToast?: ShowToastFn } = {},
): Promise<void> {
  if (deletingId.value != null) return
  deletingId.value = id
  try {
    await api(`/v1/print-jobs/${id}`, { method: 'DELETE' })
    failedJobs.value = failedJobs.value.filter((j) => j.id !== id)
    showToast?.('Druckauftrag verworfen.', 'ok')
  } catch (e: unknown) {
    showToast?.(getErrorMessage(e, 'Verwerfen fehlgeschlagen.'), 'err')
    throw e
  } finally {
    deletingId.value = null
  }
}

export async function retryJob(
  id: number,
  { showToast, onFailed }: { showToast?: ShowToastFn; onFailed?: (job: PrintJobSummary) => void } = {},
): Promise<PrintJobSummary> {
  if (retryingId.value != null) return fetchJob(id)
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
  } catch (e: unknown) {
    showToast?.(getErrorMessage(e, 'Erneut drucken fehlgeschlagen.'), 'err')
    throw e
  } finally {
    retryingId.value = null
  }
}

let waiterPollTimer: ReturnType<typeof setInterval> | null = null

export function startWaiterPrintFailurePolling(
  getContext: () => { eventId: number | null; waiterUuid: string | null },
): void {
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

export function stopWaiterPrintFailurePolling(): void {
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
    deletingId,
    failureLabel,
    watchJobIds,
    loadFailedJobs,
    retryJob,
    deleteJob,
    fetchJob,
    startWaiterPrintFailurePolling,
    stopWaiterPrintFailurePolling,
  }
}
