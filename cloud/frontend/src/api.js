const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export function apiBaseUrl() {
  return API_BASE
}

/**
 * Build absolute URL for API paths (always starts with /).
 */
export function apiUrl(path) {
  const p = path.startsWith('/') ? path : `/${path}`
  return `${API_BASE}${p}`
}

/**
 * Refresh access token using HttpOnly refresh cookie.
 * Requires credentials: 'include' on cross-origin requests.
 */
export async function refreshAccessToken() {
  const res = await fetch(apiUrl('/auth/refresh'), {
    method: 'POST',
    credentials: 'include',
  })
  if (!res.ok) return false
  const data = await res.json().catch(() => null)
  if (!data?.access_token) return false
  localStorage.setItem('access_token', data.access_token)
  localStorage.setItem('is_admin', data.is_admin ? 'true' : 'false')
  if (data.user_id != null) {
    localStorage.setItem('user_id', String(data.user_id))
  }
  return true
}

/**
 * Fetch API with Bearer token, cookies for refresh, and one 401 retry after refresh.
 */
export async function apiFetch(path, options = {}) {
  const { _retry, ...rest } = options
  const url = path.startsWith('http') ? path : apiUrl(path)
  const headers = new Headers(rest.headers || {})
  const token = localStorage.getItem('access_token')
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`)
  }
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
    return res
  }

  const headers2 = new Headers(rest.headers || {})
  const newToken = localStorage.getItem('access_token')
  if (newToken) {
    headers2.set('Authorization', `Bearer ${newToken}`)
  }

  return fetch(url, {
    ...rest,
    headers: headers2,
    credentials,
  })
}
