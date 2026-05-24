import { computed, unref } from 'vue'
import { matchesActiveOrganisation } from '../utils/orgScope'

/**
 * Filter a list by active organisation id (reactive when list or id changes).
 */
export function useOrganisationFilteredList(itemsRef, activeOrganisationIdRef, getOrganisationId) {
  return computed(() => {
    const items = unref(itemsRef) || []
    const activeOrganisationId = unref(activeOrganisationIdRef)
    return items.filter((item) =>
      matchesActiveOrganisation(activeOrganisationId, getOrganisationId(item)),
    )
  })
}

export { matchesActiveOrganisation }
