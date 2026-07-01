import type { AccessibleOrganisation } from '@/types/ui'

/**
 * Whether an item belongs to the active organisation filter.
 * When no active org is set, all items match (full list).
 */
export function matchesActiveOrganisation(
  activeOrganisationId: number | string | null | undefined,
  itemOrganisationId: number | string | null | undefined,
): boolean {
  if (activeOrganisationId == null || activeOrganisationId === '') return true
  return Number(itemOrganisationId) === Number(activeOrganisationId)
}

/**
 * Whether accounting account fields should be shown for the active organisation.
 */
export function organisationAccountsEnabled(
  organisations: Pick<AccessibleOrganisation, 'id' | 'accounts_enabled'>[],
  organisationId: number | null | undefined,
): boolean {
  if (organisationId == null) return false
  const org = organisations.find((row) => Number(row.id) === Number(organisationId))
  return Boolean(org?.accounts_enabled)
}

/**
 * Whether ingredient stock should be shown for the active organisation.
 */
export function organisationIngredientsEnabled(
  organisations: Pick<AccessibleOrganisation, 'id' | 'ingredients_enabled'>[],
  organisationId: number | null | undefined,
): boolean {
  if (organisationId == null) return false
  const org = organisations.find((row) => Number(row.id) === Number(organisationId))
  return Boolean(org?.ingredients_enabled)
}
