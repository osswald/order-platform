import { ref, unref, watch, type Ref } from 'vue'
import { apiJson } from '../api'
import { normalizeOrganisationId } from '../utils/orgId'
import type { DashboardSummary } from '@/types/ui'
import { isApiError } from '@/types/api'

function resolveOrganisationId(activeOrganisationIdRef: Ref<number | null> | number | null) {
  return normalizeOrganisationId(unref(activeOrganisationIdRef))
}

export function useDashboardSummary(activeOrganisationIdRef: Ref<number | null> | number | null) {
  const loading = ref(false)
  const loadError = ref('')
  const summary = ref<DashboardSummary | null>(null)

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
      summary.value = await apiJson<DashboardSummary>(`/organisations/${orgId}/dashboard-summary`)
    } catch (e: unknown) {
      loadError.value = isApiError(e)
        ? e.message || 'Dashboard konnte nicht geladen werden.'
        : 'Dashboard konnte nicht geladen werden.'
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
