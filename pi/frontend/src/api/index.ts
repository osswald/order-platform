import { apiJson, apiClient, assertApiData, createApiError, getApiBase, isAndroidApp, setApiBase } from './client'

export async function api<T = unknown>(path: string, options: RequestInit = {}): Promise<T> {
  return apiJson<T>(path, options)
}

export {
  apiClient,
  apiJson,
  assertApiData,
  createApiError,
  getApiBase,
  isAndroidApp,
  setApiBase,
}
