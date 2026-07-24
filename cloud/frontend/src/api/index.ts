export { api, assertApiData, apiGet, apiPost, apiPut, apiDelete } from './client'
export {
  apiBaseUrl,
  apiUrl,
  apiFetch,
  clearAuthStorage,
  isAuthSessionActive,
  markAuthSessionActive,
  refreshAccessToken,
  buildApiHeaders,
  createApiError,
  errorFromResponse,
} from './auth'

import { apiFetch, createApiError } from './auth'
import { readApiErrorFromBody } from '@/utils/apiError'

export interface ApiJsonOptions extends RequestInit {
  method?: string
}

/** JSON API helper with auth refresh; uses fetch for dynamic paths. Prefer apiGet/apiPost for static OpenAPI paths. */
export async function apiJson<T = unknown>(path: string, options: ApiJsonOptions = {}): Promise<T> {
  const res = await apiFetch(path, options)
  const text = await res.text()
  let data: unknown = null
  if (text) {
    try {
      data = JSON.parse(text) as unknown
    } catch {
      data = text
    }
  }
  if (!res.ok) {
    const message = readApiErrorFromBody(data, text || res.statusText)
    throw createApiError(message, res.status, (data as { detail?: unknown })?.detail ?? data)
  }
  return data as T
}
