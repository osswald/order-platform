import { parseApiErrorDetail } from '@vendiqo/frontend-shared/apiError'

const STORAGE_KEY = 'pi_api_base'
const DEFAULT_API_BASE = 'http://127.0.0.1:8001'
const ANDROID_API_BASE = 'http://192.168.192.10'
const PI_BACKEND_PORT = '8001'

export function isAndroidApp(): boolean {
  if (import.meta.env.VITE_ANDROID_APP === 'true') return true
  if (typeof window === 'undefined') return false
  return Boolean(window.AndroidPrinter) || /PiFrontendAndroid/i.test(window.navigator?.userAgent || '')
}

function defaultApiBase(): string {
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

export function getApiBase(): string {
  if (typeof localStorage === 'undefined') {
    return defaultApiBase()
  }
  const stored = localStorage.getItem(STORAGE_KEY)
  return (stored || defaultApiBase()).replace(/\/$/, '')
}

export function setApiBase(url: string): void {
  const t = (url || '').trim().replace(/\/$/, '')
  if (!t) {
    localStorage.removeItem(STORAGE_KEY)
    return
  }
  localStorage.setItem(STORAGE_KEY, t)
}

export function buildApiUrl(base: string, path: string): string {
  return `${base}${path.startsWith('/') ? path : `/${path}`}`
}

function fallbackPiBackendBase(base: string): string | null {
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

function isFetchNetworkError(error: unknown): boolean {
  return error instanceof TypeError
}

function requestPath(input: RequestInfo | URL): string {
  if (typeof input === 'string') {
    const parsed = new URL(input, getApiBase())
    return `${parsed.pathname}${parsed.search}`
  }
  if (input instanceof URL) {
    return `${input.pathname}${input.search}`
  }
  return `${input.url.replace(/^[^/]*\/\/[^/]+/, '')}`
}

export async function piFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const path = requestPath(input)
  const base = getApiBase()
  const requestOptions: RequestInit = {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
  }
  const url = buildApiUrl(base, path)
  try {
    return await fetch(url, requestOptions)
  } catch (error) {
    const fallbackBase = fallbackPiBackendBase(base)
    if (!fallbackBase || !isFetchNetworkError(error)) throw error
    const fallbackUrl = buildApiUrl(fallbackBase, path)
    const res = await fetch(fallbackUrl, requestOptions)
    try {
      setApiBase(fallbackBase)
    } catch {
      /* storage unavailable */
    }
    return res
  }
}

export function createApiError(message: string, status?: number, detail?: unknown): Error {
  const err = new Error(message) as Error & { status?: number; detail?: unknown }
  err.status = status
  err.detail = detail
  return err
}

export async function parseApiResponse(res: Response): Promise<unknown> {
  const text = await res.text()
  let data: unknown
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = text
  }
  if (!res.ok) {
    const detail = parseApiErrorDetail(data, text || res.statusText)
    throw createApiError(detail || res.statusText, res.status, data)
  }
  return data
}
