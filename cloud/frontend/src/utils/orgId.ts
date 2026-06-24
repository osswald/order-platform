/**
 * Coerce route/query, PrimeVue Select, or ref values to a numeric organisation id.
 */
export function normalizeOrganisationId(value: unknown): number | null {
  if (value == null || value === '') return null
  if (typeof value === 'object') {
    const record = value as { id?: unknown }
    if (typeof record.id !== 'undefined' && record.id !== null) {
      return normalizeOrganisationId(record.id)
    }
    return null
  }
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}
