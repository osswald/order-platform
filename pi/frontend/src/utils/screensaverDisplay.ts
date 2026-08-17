import { buildApiUrl, getApiBase } from '@/api/base'

export type ScreensaverDisplayUrls = {
  urls: string[]
  greyscale: boolean
}

function screensaverImagePath(sha256: string) {
  return `/v1/screensaver/${encodeURIComponent(sha256)}`
}

async function fetchJson(path: string): Promise<unknown> {
  const res = await fetch(buildApiUrl(getApiBase(), path))
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

async function fetchBlob(path: string): Promise<Blob> {
  const res = await fetch(buildApiUrl(getApiBase(), path))
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.blob()
}

/** Load gallery images via fetch + blob URLs (Android WebView cannot reliably decode huge HTTP imgs). */
export async function loadScreensaverObjectUrls(eventId: number): Promise<ScreensaverDisplayUrls> {
  try {
    const data = (await fetchJson(
      `/v1/screensaver/images?event_id=${encodeURIComponent(String(eventId))}`,
    )) as { images?: Array<{ sha256: string }>; greyscale?: boolean }
    const hashes = (data.images || []).map((i) => String(i.sha256 || '').trim()).filter(Boolean)
    const urls: string[] = []
    for (const sha of hashes) {
      try {
        const blob = await fetchBlob(screensaverImagePath(sha))
        urls.push(URL.createObjectURL(blob))
      } catch {
        /* skip a single failed image */
      }
    }
    return { urls, greyscale: Boolean(data.greyscale) }
  } catch {
    return { urls: [], greyscale: false }
  }
}

export function revokeScreensaverObjectUrls(urls: string[]) {
  for (const url of urls) {
    if (url.startsWith('blob:')) {
      try {
        URL.revokeObjectURL(url)
      } catch {
        /* ignore */
      }
    }
  }
}
