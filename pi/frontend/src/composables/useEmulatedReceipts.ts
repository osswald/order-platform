import { onMounted, onUnmounted, ref } from 'vue'
import { api } from '@/api'
import type { EmulatedReceiptSummary } from '@/types/api'

export interface UseEmulatedReceiptsOptions {
  pollMs?: number
  autoStart?: boolean
}

export function useEmulatedReceipts({ pollMs = 2000, autoStart = true }: UseEmulatedReceiptsOptions = {}) {
  const receipts = ref<EmulatedReceiptSummary[]>([])
  const loading = ref(false)
  let pollTimer: ReturnType<typeof setInterval> | null = null

  async function refresh(): Promise<void> {
    loading.value = true
    try {
      receipts.value = await api<EmulatedReceiptSummary[]>('/v1/emulated-receipts')
    } catch {
      receipts.value = []
    } finally {
      loading.value = false
    }
  }

  function startPolling(): void {
    stopPolling()
    pollTimer = setInterval(refresh, pollMs)
  }

  function stopPolling(): void {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  if (autoStart) {
    onMounted(() => {
      refresh()
      startPolling()
    })
    onUnmounted(stopPolling)
  }

  return {
    receipts,
    loading,
    refresh,
    startPolling,
    stopPolling,
  }
}

export function formatReceiptTime(iso: string | null | undefined): string {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString('de-CH')
  } catch {
    return iso
  }
}
