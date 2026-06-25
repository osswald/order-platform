import createClient from 'openapi-fetch'
import type { paths } from '@/types/api.generated'
import { createApiError, getApiBase, parseApiResponse, piFetch } from './base'

export const apiClient = createClient<paths>({
  baseUrl: getApiBase(),
  fetch: piFetch,
})

type ApiResult<T> = {
  data?: T
  error?: unknown
  response: Response
}

export function assertApiData<T>(result: ApiResult<T>): T {
  const { data, error, response } = result
  if (error || !response.ok) {
    const message =
      error instanceof Error
        ? error.message
        : typeof error === 'string'
          ? error
          : response.statusText || 'Request failed'
    throw createApiError(message, response.status, error ?? data)
  }
  if (data === undefined) {
    throw createApiError('Empty response', response.status)
  }
  return data
}

/** JSON fetch wrapper used across the Pi frontend. */
export async function apiJson<T = unknown>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json')
  }
  const res = await piFetch(path, { ...options, headers })
  return (await parseApiResponse(res)) as T
}

export { createApiError, getApiBase, isAndroidApp, piFetch, setApiBase } from './base'
