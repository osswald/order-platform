/**
 * Whether an item belongs to the active organisation filter.
 * When no active org is set, all items match (full list).
 */
export function matchesActiveOrganisation(activeOrganisationId, itemOrganisationId) {
  if (activeOrganisationId == null || activeOrganisationId === '') return true
  return Number(itemOrganisationId) === Number(activeOrganisationId)
}
