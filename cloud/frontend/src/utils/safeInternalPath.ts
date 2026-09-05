/**
 * Return a same-origin relative path for window.location navigation.
 * Rejects protocol-relative, off-origin, and non-http(s) values.
 */
export function safeInternalPath(candidate: unknown, fallback: string): string {
  if (typeof candidate !== 'string' || candidate === '') {
    return fallback
  }
  if (candidate.includes('\\')) {
    return fallback
  }
  try {
    const url = new URL(candidate, window.location.origin)
    if (url.origin !== window.location.origin) {
      return fallback
    }
    if (url.protocol !== 'http:' && url.protocol !== 'https:') {
      return fallback
    }
    return `${url.pathname}${url.search}${url.hash}`
  } catch {
    return fallback
  }
}
