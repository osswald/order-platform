import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  loadScreensaverObjectUrls,
  revokeScreensaverObjectUrls,
} from '@/utils/screensaverDisplay'

describe('screensaverDisplay', () => {
  beforeEach(() => {
    vi.spyOn(URL, 'createObjectURL').mockImplementation((obj: Blob | MediaSource) =>
      `blob:test-${obj instanceof Blob ? obj.size : 0}`,
    )
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('fetches each hash as a blob object URL instead of a raw http img src', async () => {
    const jpeg = new Blob([new Uint8Array([1, 2, 3, 4])], { type: 'image/jpeg' })
    const sha = 'ab'.repeat(32)
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/v1/screensaver/images')) {
        return new Response(JSON.stringify({ images: [{ sha256: sha }], greyscale: true }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      }
      if (url.includes(`/v1/screensaver/${sha}`)) {
        return new Response(jpeg, { status: 200, headers: { 'Content-Type': 'image/jpeg' } })
      }
      return new Response('nope', { status: 404 })
    })
    vi.stubGlobal('fetch', fetchMock)

    const result = await loadScreensaverObjectUrls(11)
    expect(result.greyscale).toBe(true)
    expect(result.urls).toEqual(['blob:test-4'])
    expect(fetchMock.mock.calls.some((c) => String(c[0]).includes(`/v1/screensaver/${sha}`))).toBe(
      true,
    )
  })

  it('returns empty urls when the manifest request fails', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('err', { status: 500 })))
    const result = await loadScreensaverObjectUrls(11)
    expect(result).toEqual({ urls: [], greyscale: false })
  })

  it('revokes previously created object URLs', () => {
    revokeScreensaverObjectUrls(['blob:test-1', 'blob:test-2'])
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:test-1')
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:test-2')
  })
})
