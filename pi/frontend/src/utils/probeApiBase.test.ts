import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { getApiBase, setApiBase } from '@/api/base'
import { PLAY_REVIEW_DEMO_API_BASE, PROBE_TIMEOUT_MS, probeApiBase } from '@/utils/probeApiBase'

describe('probeApiBase', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.stubGlobal('fetch', vi.fn())
    delete (window as Window & { AndroidNetwork?: unknown }).AndroidNetwork
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    delete (window as Window & { AndroidNetwork?: unknown }).AndroidNetwork
  })

  it('returns reachable when health responds ok', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ status: 'ok' }), { status: 200 }))
    const result = await probeApiBase('http://192.168.192.10')
    expect(result).toEqual({ reachable: true })
    expect(fetch).toHaveBeenCalledWith('http://192.168.192.10/health', {
      method: 'GET',
      signal: expect.any(AbortSignal),
      credentials: 'omit',
    })
  })

  it('returns network reason on fetch failure', async () => {
    vi.mocked(fetch).mockRejectedValue(new TypeError('Failed to fetch'))
    const result = await probeApiBase('http://192.168.192.10')
    expect(result).toEqual({ reachable: false, reason: 'network' })
  })

  it('returns network reason when probe times out', async () => {
    vi.mocked(fetch).mockImplementation((_url, init) => {
      return new Promise((_resolve, reject) => {
        const signal = init?.signal
        if (!signal) {
          reject(new Error('missing abort signal'))
          return
        }
        if (signal.aborted) {
          reject(signal.reason ?? new DOMException('Aborted', 'AbortError'))
          return
        }
        signal.addEventListener('abort', () => {
          reject(signal.reason ?? new DOMException('Aborted', 'AbortError'))
        })
      })
    })
    vi.useFakeTimers()
    const pending = probeApiBase('http://192.168.192.10')
    await vi.advanceTimersByTimeAsync(PROBE_TIMEOUT_MS)
    const result = await pending
    vi.useRealTimers()
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
    expect(fetch).toHaveBeenCalledWith('http://10.0.0.5/health', {
      method: 'GET',
      signal: expect.any(AbortSignal),
      credentials: 'omit',
    })
    expect(getApiBase()).toBe('http://10.0.0.5')
  })

  it('exports play review demo url constant and timeout', () => {
    expect(PLAY_REVIEW_DEMO_API_BASE).toBe('https://play-review.demo.vendiqo.ch')
    expect(PROBE_TIMEOUT_MS).toBe(2500)
  })

  it('still times out when AbortSignal.timeout is unavailable', async () => {
    const originalTimeout = AbortSignal.timeout
    // Older Android WebViews may lack AbortSignal.timeout.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    delete (AbortSignal as any).timeout
    vi.mocked(fetch).mockImplementation((_url, init) => {
      return new Promise((_resolve, reject) => {
        const signal = init?.signal
        if (!signal) {
          reject(new Error('missing abort signal'))
          return
        }
        signal.addEventListener('abort', () => {
          reject(signal.reason ?? new DOMException('Aborted', 'AbortError'))
        })
      })
    })
    vi.useFakeTimers()
    try {
      const pending = probeApiBase('https://play-review.demo.vendiqo.ch')
      expect(fetch).toHaveBeenCalled()
      await Promise.resolve()
      const early = await Promise.race([
        pending.then((r) => ({ done: true as const, r })),
        Promise.resolve({ done: false as const }),
      ])
      expect(early.done).toBe(false)
      await vi.advanceTimersByTimeAsync(PROBE_TIMEOUT_MS)
      const result = await pending
      expect(result).toEqual({ reachable: false, reason: 'network' })
    } finally {
      vi.useRealTimers()
      AbortSignal.timeout = originalTimeout
    }
  })

  it('uses AndroidNetwork bridge when available and skips fetch', async () => {
    const probeHealth = vi.fn(() => JSON.stringify({ ok: true, status: 'ok' }))
    ;(window as Window & { AndroidNetwork?: { probeHealth: (u: string) => string } }).AndroidNetwork = {
      probeHealth,
    }
    const result = await probeApiBase('https://play-review.demo.vendiqo.ch')
    expect(result).toEqual({ reachable: true })
    expect(probeHealth).toHaveBeenCalledWith('https://play-review.demo.vendiqo.ch')
    expect(fetch).not.toHaveBeenCalled()
  })

  it('maps AndroidNetwork bridge failure to probe result', async () => {
    ;(window as Window & { AndroidNetwork?: { probeHealth: (u: string) => string } }).AndroidNetwork = {
      probeHealth: () => JSON.stringify({ ok: false, reason: 'http', message: 'HTTP 503' }),
    }
    const result = await probeApiBase('https://play-review.demo.vendiqo.ch')
    expect(result).toEqual({ reachable: false, reason: 'http', message: 'HTTP 503' })
    expect(fetch).not.toHaveBeenCalled()
  })

  it('falls back to fetch when AndroidNetwork bridge throws', async () => {
    ;(window as Window & { AndroidNetwork?: { probeHealth: (u: string) => string } }).AndroidNetwork = {
      probeHealth: () => {
        throw new Error('bridge down')
      },
    }
    vi.mocked(fetch).mockResolvedValue(new Response('{"status":"ok"}', { status: 200 }))
    const result = await probeApiBase('https://play-review.demo.vendiqo.ch')
    expect(result).toEqual({ reachable: true })
    expect(fetch).toHaveBeenCalled()
  })
})
