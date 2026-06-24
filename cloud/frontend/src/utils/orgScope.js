/**
 * Whether an item belongs to the active organisation filter.
 * When no active org is set, all items match (full list).
 */
export function matchesActiveOrganisation(activeOrganisationId, itemOrganisationId) {
  if (activeOrganisationId == null || activeOrganisationId === '') return true
  return Number(itemOrganisationId) === Number(activeOrganisationId)
}

/**
 * Whether accounting account fields should be shown for the active organisation.
 */
export function organisationAccountsEnabled(organisations, organisationId) {
  if (organisationId == null) return false
  const org = organisations.find((row) => Number(row.id) === Number(organisationId))
  return Boolean(org?.accounts_enabled)
}
