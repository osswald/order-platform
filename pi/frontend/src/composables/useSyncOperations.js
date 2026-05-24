import { ref } from 'vue'
import { api, getApiBase, setApiBase } from '../api'
import { useBundle } from './useBundle'

export function useSyncOperations() {
  const { busy, syncError, refreshBundle, showToast } = useBundle()
  const syncStatus = ref(null)

  async function loadSyncStatus() {
    try {
      syncStatus.value = await api('/v1/sync/status')
    } catch {
      syncStatus.value = null
    }
  }

  function saveApiBase(url) {
    const trimmed = (url || '').trim()
    if (trimmed) {
      setApiBase(trimmed)
    } else {
      localStorage.removeItem('pi_api_base')
    }
    showToast('API-Basis gespeichert.', 'ok')
    return getApiBase()
  }

  async function pullConfiguration() {
    busy.value = true
    syncError.value = ''
    try {
      const pull = await api('/v1/sync/pull', { method: 'POST' })
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
    } catch (error) {
      syncError.value = error.message || 'Laden fehlgeschlagen'
      showToast(syncError.value, 'err')
      throw error
    } finally {
      busy.value = false
    }
  }

  async function pushOutbox() {
    const result = await api('/v1/sync/push', { method: 'POST' })
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
