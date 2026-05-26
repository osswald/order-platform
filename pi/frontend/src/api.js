import { parseApiErrorDetail } from './utils/apiError'

const STORAGE_KEY = 'pi_api_base'
const DEFAULT_API_BASE = 'http://127.0.0.1:8001'
const ANDROID_API_BASE = 'http://localhost:8001'

export function isAndroidApp() {
  if (import.meta.env.VITE_ANDROID_APP === 'true') return true
  if (typeof window === 'undefined') return false
  return Boolean(window.AndroidPrinter) || /PiFrontendAndroid/i.test(window.navigator?.userAgent || '')
}

function defaultApiBase() {
  if (import.meta.env.VITE_API_BASE) return import.meta.env.VITE_API_BASE.replace(/\/$/, '')
  if (isAndroidApp()) return ANDROID_API_BASE
  if (typeof window !== 'undefined') {
    const host = window.location.hostname
    if (host && host !== 'localhost' && host !== '127.0.0.1') {
      return window.location.origin.replace(/\/$/, '')
    }
  }
  return DEFAULT_API_BASE
}

export function getApiBase() {
  if (typeof localStorage === 'undefined') {
    return defaultApiBase()
  }
  const stored = localStorage.getItem(STORAGE_KEY)
  const base = (stored || defaultApiBase()).replace(/\/$/, '')
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
    const detail = parseApiErrorDetail(data, text || res.statusText)
    const err = new Error(detail || res.statusText)
    err.status = res.status
    throw err
  }
  return data
}
