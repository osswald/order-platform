import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { getApiBase, setApiBase } from '@/api/base'
import { PLAY_REVIEW_DEMO_API_BASE, probeApiBase } from '@/utils/probeApiBase'

describe('probeApiBase', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('returns reachable when health responds ok', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ status: 'ok' }), { status: 200 }))
    const result = await probeApiBase('http://192.168.192.10')
    expect(result).toEqual({ reachable: true })
    expect(fetch).toHaveBeenCalledWith('http://192.168.192.10/health', { method: 'GET' })
  })

  it('returns network reason on fetch failure', async () => {
    vi.mocked(fetch).mockRejectedValue(new TypeError('Failed to fetch'))
    const result = await probeApiBase('http://192.168.192.10')
    expect(result).toEqual({ reachable: false, reason: 'network' })
  })

  it('returns http reason on non-ok status', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response('bad', { status: 503 }))
    const result = await probeApiBase('http://192.168.192.10')
    expect(result.reachable).toBe(false)
    if (!result.reachable) {
      expect(result.reason).toBe('http')
    }
  })

  it('uses stored api base when no argument passed', async () => {
    setApiBase('http://10.0.0.5')
    vi.mocked(fetch).mockResolvedValue(new Response('{}', { status: 200 }))
    await probeApiBase()
    expect(fetch).toHaveBeenCalledWith('http://10.0.0.5/health', { method: 'GET' })
    expect(getApiBase()).toBe('http://10.0.0.5')
  })

  it('exports play review demo url constant', () => {
    expect(PLAY_REVIEW_DEMO_API_BASE).toBe('https://play-review.demo.vendiqo.ch')
  })
})
