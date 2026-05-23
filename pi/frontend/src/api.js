const STORAGE_KEY = 'pi_api_base'

export function getApiBase() {
  if (typeof localStorage === 'undefined') {
    return (import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8001').replace(/\/$/, '')
  }
  const stored = localStorage.getItem(STORAGE_KEY)
  const base = (stored || import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8001').replace(/\/$/, '')
  return base
}

export function setApiBase(url) {
  const t = (url || '').trim().replace(/\/$/, '')
  if (!t) {
    localStorage.removeItem(STORAGE_KEY)
    return
  }
  localStorage.setItem(STORAGE_KEY, t)
}

export async function api(path, options = {}) {
  const base = getApiBase()
  const url = `${base}${path.startsWith('/') ? path : `/${path}`}`
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  })
  const text = await res.text()
  let data
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = text
  }
  if (!res.ok) {
    let detail = text
    if (typeof data === 'object' && data !== null) {
      if (typeof data.detail === 'string') detail = data.detail
      else if (Array.isArray(data.detail)) detail = data.detail.map((e) => e?.msg || JSON.stringify(e)).join('; ')
      else if (data.detail) detail = JSON.stringify(data.detail)
    }
    const err = new Error(detail || res.statusText)
    err.status = res.status
    throw err
  }
  return data
}
