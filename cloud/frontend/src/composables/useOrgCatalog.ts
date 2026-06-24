import { apiJson } from '@/api'
import type { ArticleRead, WaiterRead } from '@/types/api'

export interface OrgCatalogData {
  articles: ArticleRead[]
  waiters: WaiterRead[]
}

const cache = new Map<string, OrgCatalogData>()
const inflight = new Map<string, Promise<OrgCatalogData>>()

function cacheKey(organisationId: number | null | undefined): string {
  return organisationId == null ? 'all' : String(organisationId)
}

function buildArticlesUrl(organisationId: number | null | undefined): string {
  const params = new URLSearchParams({ minimal: 'true' })
  if (organisationId != null) params.set('organisation_id', String(organisationId))
  return `/articles/?${params}`
}

function buildWaitersUrl(organisationId: number | null | undefined): string {
  if (organisationId == null) return '/waiters/'
  return `/waiters/?organisation_id=${organisationId}`
}

async function fetchCatalog(organisationId: number | null | undefined): Promise<OrgCatalogData> {
  const [articles, waiters] = await Promise.all([
    apiJson<ArticleRead[]>(buildArticlesUrl(organisationId)),
    apiJson<WaiterRead[]>(buildWaitersUrl(organisationId)),
  ])
  return { articles, waiters }
}

export interface OrgCatalogResult extends OrgCatalogData {
  fromCache: boolean
  refreshPromise?: Promise<OrgCatalogData | null> | null
}

/**
 * Load org-scoped article/waiter catalog with in-memory session cache.
 */
export async function loadOrgCatalog(
  organisationId: number | null | undefined,
  { refresh = false } = {},
): Promise<OrgCatalogResult> {
  const key = cacheKey(organisationId)
  const cached = cache.get(key)

  if (cached && !refresh) {
    const refreshPromise = fetchCatalog(organisationId)
      .then((data) => {
        cache.set(key, data)
        return data
      })
      .catch(() => null)
    return { ...cached, fromCache: true, refreshPromise }
  }

  if (inflight.has(key)) {
    const data = await inflight.get(key)!
    return { ...data, fromCache: false }
  }

  const promise = fetchCatalog(organisationId)
  inflight.set(key, promise)
  try {
    const data = await promise
    cache.set(key, data)
    return { ...data, fromCache: false, refreshPromise: null }
  } finally {
    inflight.delete(key)
  }
}

/** Drop cached catalog for an organisation (e.g. after article/waiter CRUD). */
export function invalidateOrgCatalog(organisationId: number | null | undefined) {
  cache.delete(cacheKey(organisationId))
  cache.delete('all')
}
