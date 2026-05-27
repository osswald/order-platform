/**
 * Coerce route/query, PrimeVue Select, or ref values to a numeric organisation id.
 */
export function normalizeOrganisationId(value) {
  if (value == null || value === '') return null
  if (typeof value === 'object') {
    if (typeof value.id !== 'undefined' && value.id !== null) {
      return normalizeOrganisationId(value.id)
    }
    return null
  }
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}
