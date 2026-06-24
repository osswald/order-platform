import createClient, { type Middleware } from 'openapi-fetch'
import type { paths } from '@/types/api.generated'
import {
  apiBaseUrl,
  buildApiHeaders,
  clearAuthStorage,
  createApiError,
  errorFromResponse,
  refreshAccessToken,
} from './auth'

const retryMap = new WeakMap<Request, boolean>()

const authMiddleware: Middleware = {
  onRequest({ request }) {
    const headers = buildApiHeaders(request.headers)
    headers.forEach((value, key) => {
      request.headers.set(key, value)
    })
    return request
  },
  async onResponse({ request, response }) {
    if (response.status !== 401 || retryMap.get(request)) {
      return response
    }
    const refreshed = await refreshAccessToken()
    if (!refreshed) {
      clearAuthStorage()
      return response
    }
    retryMap.set(request, true)
    const retryHeaders = buildApiHeaders(request.headers)
    return fetch(request.url, {
      method: request.method,
      headers: retryHeaders,
      body: request.body,
      credentials: 'include',
    })
  },
}

export const api = createClient<paths>({
  baseUrl: apiBaseUrl(),
  credentials: 'include',
})

api.use(authMiddleware)

type ApiResult<T> = {
  data?: T
  error?: unknown
  response: Response
}

export function assertApiData<T>(result: ApiResult<T>): T {
  const { data, error, response } = result
  if (error || !response.ok) {
    throw errorFromResponse(error ?? data, response)
  }
  if (data === undefined) {
    throw createApiError('Empty response', response.status)
  }
  return data
}

export async function apiGet(
  path: Parameters<typeof api.GET>[0],
  init?: Parameters<typeof api.GET>[1],
): Promise<unknown> {
  const result = await api.GET(path, init)
  return assertApiData(result)
}

export async function apiPost(
  path: Parameters<typeof api.POST>[0],
  init: Parameters<typeof api.POST>[1],
): Promise<unknown> {
  const result = await api.POST(path, init)
  return assertApiData(result)
}

export async function apiPut(
  path: Parameters<typeof api.PUT>[0],
  init: Parameters<typeof api.PUT>[1],
): Promise<unknown> {
  const result = await api.PUT(path, init)
  return assertApiData(result)
}

export async function apiDelete(
  path: Parameters<typeof api.DELETE>[0],
  init?: Parameters<typeof api.DELETE>[1],
): Promise<unknown> {
  const result = await api.DELETE(path, init)
  if (!result.response.ok && result.response.status !== 204) {
    throw errorFromResponse(result.error ?? result.data, result.response)
  }
  return result.data
}
