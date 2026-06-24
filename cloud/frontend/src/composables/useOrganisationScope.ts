import { computed, toValue } from 'vue'
import type { MaybeRefOrGetter } from 'vue'
import { matchesActiveOrganisation } from '@/utils/orgScope'

/**
 * Filter a list by active organisation id (reactive when list or id changes).
 */
export function useOrganisationFilteredList<T>(
  itemsRef: MaybeRefOrGetter<T[] | null | undefined>,
  activeOrganisationIdRef: MaybeRefOrGetter<number | null | undefined>,
  getOrganisationId: (item: T) => number | string | null | undefined,
) {
  return computed(() => {
    const items = toValue(itemsRef) || []
    const activeOrganisationId = toValue(activeOrganisationIdRef)
    return items.filter((item) =>
      matchesActiveOrganisation(activeOrganisationId, getOrganisationId(item)),
    )
  })
}

export { matchesActiveOrganisation }
