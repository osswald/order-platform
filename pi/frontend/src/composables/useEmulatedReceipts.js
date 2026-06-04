import { onMounted, onUnmounted, ref } from 'vue'
import { api } from '../api'

export function useEmulatedReceipts({ pollMs = 2000, autoStart = true } = {}) {
  const receipts = ref([])
  const loading = ref(false)
  let pollTimer = null

  async function refresh() {
    loading.value = true
    try {
      receipts.value = await api('/v1/emulated-receipts')
    } catch {
      receipts.value = []
    } finally {
      loading.value = false
    }
  }

  function startPolling() {
    stopPolling()
    pollTimer = setInterval(refresh, pollMs)
  }

  function stopPolling() {
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

export function formatReceiptTime(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString('de-CH')
  } catch {
    return iso
  }
}
