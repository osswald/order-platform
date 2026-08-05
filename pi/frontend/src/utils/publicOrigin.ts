import { getApiBase, isAndroidApp } from '@/api/base'

/**
 * Origin for shareable / openable PWA URLs.
 * On Android the WebView origin is the asset loader (`appassets…`); use the Pi API base instead.
 */
export function publicOrigin(): string {
  if (typeof window === 'undefined') return ''
  if (isAndroidApp()) return getApiBase().replace(/\/$/, '')
  return window.location.origin.replace(/\/$/, '')
}

/** Join public origin with a router path (must start with `/` or be normalized). */
export function absolutePublicUrl(path: string): string {
  const normalized = path.startsWith('/') ? path : `/${path}`
  const origin = publicOrigin()
  if (!origin) return normalized
  return `${origin}${normalized}`
}
