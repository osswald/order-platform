import { currentLocale } from '@/i18n'
import { readApiErrorFromBody } from '@/utils/apiError'
import type { ApiError } from '@/types/api'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export function apiBaseUrl(): string {
  return API_BASE
}

export function apiUrl(path: string): string {
  const p = path.startsWith('/') ? path : `/${path}`
  return `${API_BASE}${p}`
}

/** Remove tokens and session keys after failed auth (stale token, missing refresh cookie). */
export function clearAuthStorage(): void {
  localStorage.removeItem('access_token')
  localStorage.removeItem('user_email')
  localStorage.removeItem('is_admin')
  localStorage.removeItem('user_role')
  localStorage.removeItem('is_tenant_admin')
  localStorage.removeItem('is_organisation_admin')
  localStorage.removeItem('user_hire_company_id')
  localStorage.removeItem('active_hire_company_id')
  localStorage.removeItem('user_id')
  localStorage.removeItem('active_organisation_id')
}

export function buildApiHeaders(initHeaders?: HeadersInit): Headers {
  const headers = new Headers(initHeaders || {})
  if (!headers.has('Accept-Language')) {
    headers.set('Accept-Language', currentLocale())
  }
  const token = localStorage.getItem('access_token')
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  const hireCompanyId = localStorage.getItem('active_hire_company_id')
  if (hireCompanyId && !headers.has('X-Hire-Company-Id')) {
    headers.set('X-Hire-Company-Id', hireCompanyId)
  }
  return headers
}

export async function refreshAccessToken(): Promise<boolean> {
  const res = await fetch(apiUrl('/auth/refresh'), {
    method: 'POST',
    credentials: 'include',
    headers: { 'Accept-Language': currentLocale() },
  })
  if (!res.ok) return false
  const data = (await res.json().catch(() => null)) as Record<string, unknown> | null
  if (!data?.access_token) return false
  localStorage.setItem('access_token', String(data.access_token))
  localStorage.setItem('is_admin', data.is_admin ? 'true' : 'false')
  if (data.role) localStorage.setItem('user_role', String(data.role))
  if (data.hire_company_id != null) {
    localStorage.setItem('user_hire_company_id', String(data.hire_company_id))
  } else {
    localStorage.removeItem('user_hire_company_id')
  }
  localStorage.setItem('is_tenant_admin', data.is_tenant_admin ? 'true' : 'false')
  localStorage.setItem(
    'is_organisation_admin',
    data.is_organisation_admin ? 'true' : 'false',
  )
  if (data.user_id != null) {
    localStorage.setItem('user_id', String(data.user_id))
  }
  return true
}

export function createApiError(message: string, status?: number, detail?: unknown): ApiError {
  const err = new Error(message) as ApiError
  err.status = status
  err.detail = detail
  return err
}

export function errorFromResponse(
  data: unknown,
  response: Response,
  fallbackText?: string,
): ApiError {
  const message = readApiErrorFromBody(data, fallbackText || response.statusText)
  return createApiError(message, response.status, (data as { detail?: unknown })?.detail ?? data)
}

interface FetchWithAuthOptions extends RequestInit {
  _retry?: boolean
}

/** Raw fetch with Bearer token, cookies for refresh, and one 401 retry after refresh. */
export async function apiFetch(path: string, options: FetchWithAuthOptions = {}): Promise<Response> {
  const { _retry, ...rest } = options
  const url = path.startsWith('http') ? path : apiUrl(path)
  const headers = buildApiHeaders(rest.headers)
  const credentials = rest.credentials ?? 'include'

  const res = await fetch(url, {
    ...rest,
    headers,
    credentials,
  })

  if (res.status !== 401 || _retry) {
    return res
  }

  const refreshed = await refreshAccessToken()
  if (!refreshed) {
    if (res.status === 401) {
      clearAuthStorage()
    }
    return res
  }

  return apiFetch(path, { ...options, _retry: true })
}
