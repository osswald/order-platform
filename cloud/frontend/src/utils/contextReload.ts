/**
 * Resolve the path to hard-reload after organisation/tenant context changes.
 * Detail and create routes reload their parent list to avoid cross-org stale records.
 */
export function resolveContextReloadPath(
  routeName: string | null | undefined,
  path: string,
): string {
  const cleanPath = path.split('?')[0]
  const name = routeName == null ? '' : String(routeName)
  if (name.endsWith('-detail') || name.endsWith('-new')) {
    const segments = cleanPath.split('/').filter(Boolean)
    if (segments.length > 1) {
      return `/${segments.slice(0, -1).join('/')}`
    }
  }
  return cleanPath
}

/** Strip legacy `organisation` query param; returns id if present. */
export function readLegacyOrganisationQuery(
  query: Record<string, unknown>,
): number | null {
  const raw = query.organisation
  if (raw == null || raw === '') return null
  const id = Number(raw)
  return Number.isFinite(id) ? id : null
}
