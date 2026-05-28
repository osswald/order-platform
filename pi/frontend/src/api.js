import { parseApiErrorDetail } from './utils/apiError'

const STORAGE_KEY = 'pi_api_base'
const DEFAULT_API_BASE = 'http://127.0.0.1:8001'
const ANDROID_API_BASE = 'http://localhost:8001'
const PI_BACKEND_PORT = '8001'

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

function buildApiUrl(base, path) {
  return `${base}${path.startsWith('/') ? path : `/${path}`}`
}

function fallbackPiBackendBase(base) {
  try {
    const parsed = new URL(base)
    if (!/^https?:$/.test(parsed.protocol)) return null
    if (parsed.port) return null
    if ((parsed.pathname || '/') !== '/') return null
    parsed.port = PI_BACKEND_PORT
    parsed.pathname = ''
    return parsed.toString().replace(/\/$/, '')
  } catch {
    return null
  }
}

function isFetchNetworkError(error) {
  return error instanceof TypeError
}

export async function api(path, options = {}) {
  const base = getApiBase()
  const requestOptions = {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  }
  const url = buildApiUrl(base, path)
  let res
  try {
    res = await fetch(url, requestOptions)
  } catch (error) {
    const fallbackBase = fallbackPiBackendBase(base)
    if (!fallbackBase || !isFetchNetworkError(error)) throw error
    const fallbackUrl = buildApiUrl(fallbackBase, path)
    res = await fetch(fallbackUrl, requestOptions)
    try {
      setApiBase(fallbackBase)
    } catch {
      /* storage unavailable */
    }
  }
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
