import { ref, unref, watch } from 'vue'
import { apiFetch } from '../api'
import { normalizeOrganisationId } from '../utils/orgId'

function resolveOrganisationId(activeOrganisationIdRef) {
  return normalizeOrganisationId(unref(activeOrganisationIdRef))
}

export function useDashboardSummary(activeOrganisationIdRef) {
  const loading = ref(false)
  const loadError = ref('')
  const summary = ref(null)

  async function load() {
    const orgId = resolveOrganisationId(activeOrganisationIdRef)
    if (orgId == null) {
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
    () => resolveOrganisationId(activeOrganisationIdRef),
    () => {
      load()
    },
    { immediate: true },
  )

  return { summary, loading, loadError, reload: load }
}
