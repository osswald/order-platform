import { apiJson } from '../api'

/** @type {Map<string, { articles: object[], waiters: object[] }>} */
const cache = new Map()

/** @type {Map<string, Promise<{ articles: object[], waiters: object[] }>>} */
const inflight = new Map()

function cacheKey(organisationId) {
  return organisationId == null ? 'all' : String(organisationId)
}

function buildArticlesUrl(organisationId) {
  const params = new URLSearchParams({ minimal: 'true' })
  if (organisationId != null) params.set('organisation_id', String(organisationId))
  return `/articles/?${params}`
}

function buildWaitersUrl(organisationId) {
  if (organisationId == null) return '/waiters/'
  return `/waiters/?organisation_id=${organisationId}`
}

async function fetchCatalog(organisationId) {
  const [articles, waiters] = await Promise.all([
    apiJson(buildArticlesUrl(organisationId)),
    apiJson(buildWaitersUrl(organisationId)),
  ])
  return { articles, waiters }
}

/**
 * Load org-scoped article/waiter catalog with in-memory session cache.
 * @param {number|null|undefined} organisationId
 * @param {{ refresh?: boolean }} [options]
 * @returns {Promise<{ articles: object[], waiters: object[], fromCache: boolean }>}
 */
export async function loadOrgCatalog(organisationId, { refresh = false } = {}) {
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
    const data = await inflight.get(key)
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
export function invalidateOrgCatalog(organisationId) {
  cache.delete(cacheKey(organisationId))
  cache.delete('all')
}
