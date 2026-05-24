import { ref, watch } from 'vue'
import { apiFetch } from '../api'

export function useDashboardSummary(activeOrganisationIdRef) {
  const loading = ref(false)
  const loadError = ref('')
  const summary = ref(null)

  async function load() {
    const orgId = activeOrganisationIdRef?.value ?? activeOrganisationIdRef
    if (orgId == null || orgId === '') {
      summary.value = null
      loadError.value = ''
      loading.value = false
      return
    }

    loading.value = true
    loadError.value = ''
    try {
      const resp = await apiFetch(`/organisations/${orgId}/dashboard-summary`)
      if (!resp.ok) throw new Error(await resp.text())
      summary.value = await resp.json()
    } catch (e) {
      loadError.value = e.message || 'Dashboard konnte nicht geladen werden.'
      summary.value = null
    } finally {
      loading.value = false
    }
  }

  watch(
    () => (typeof activeOrganisationIdRef === 'object' ? activeOrganisationIdRef.value : activeOrganisationIdRef),
    () => {
      load()
    },
    { immediate: true },
  )

  return { summary, loading, loadError, reload: load }
}
