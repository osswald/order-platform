import { ref } from 'vue'
import { api, getApiBase, setApiBase } from '@/api'
import type { SyncStatusResponse } from '@/types/api'
import { getErrorMessage } from '@/types/api'
import { busy, syncError, refreshBundle, showToast } from '@/store'

export function useSyncOperations() {
  const syncStatus = ref<SyncStatusResponse | null>(null)

  async function loadSyncStatus(): Promise<void> {
    try {
      syncStatus.value = await api<SyncStatusResponse>('/v1/sync/status')
    } catch {
      syncStatus.value = null
    }
  }

  function saveApiBase(url: string): string {
    const trimmed = (url || '').trim()
    if (trimmed) {
      setApiBase(trimmed)
    } else {
      localStorage.removeItem('pi_api_base')
    }
    showToast('API-Basis gespeichert.', 'ok')
    return getApiBase()
  }

  async function pullConfiguration(): Promise<number> {
    busy.value = true
    syncError.value = ''
    try {
      const pull = await api<{ event_count?: number }>('/v1/sync/pull', { method: 'POST' })
      const count = await refreshBundle()
      const eventCount = pull?.event_count ?? count
      showToast(
        eventCount > 0
          ? `Konfiguration geladen (${eventCount} Event(s)).`
          : 'Sync OK, aber keine aktiven Events in der Cloud.',
        eventCount > 0 ? 'ok' : 'err',
      )
      await loadSyncStatus()
      return eventCount
    } catch (error: unknown) {
      syncError.value = getErrorMessage(error, 'Laden fehlgeschlagen')
      showToast(syncError.value, 'err')
      throw error
    } finally {
      busy.value = false
    }
  }

  async function pushOutbox(): Promise<{ errors?: unknown[] }> {
    const result = await api<{ errors?: unknown[] }>('/v1/sync/push', { method: 'POST' })
    const ok = !result.errors?.length
    showToast(ok ? 'Push OK' : 'Push mit Fehlern', ok ? 'ok' : 'err')
    await loadSyncStatus()
    return result
  }

  return {
    syncStatus,
    loadSyncStatus,
    saveApiBase,
    pullConfiguration,
    pushOutbox,
  }
}
