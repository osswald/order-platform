import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, nextTick } from 'vue'

const probeApiBase = vi.fn()

vi.mock('@/utils/probeApiBase', () => ({
  probeApiBase: (...args: unknown[]) => probeApiBase(...args),
}))

import {
  KEEPALIVE_MS,
  WARM_WINDOW_MS,
  ensureReachable,
  piLastOkAt,
  piProbing,
  piStatus,
  probeNow,
  resetPiConnectivityForTests,
  usePiConnectivityKeepalive,
} from './usePiConnectivity'

describe('usePiConnectivity', () => {
  beforeEach(() => {
    resetPiConnectivityForTests()
    probeApiBase.mockReset()
    vi.useFakeTimers()
    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      get: () => 'visible',
    })
  })

  afterEach(() => {
    vi.useRealTimers()
    resetPiConnectivityForTests()
  })

  it('marks reachable and records lastOkAt on successful probe', async () => {
    probeApiBase.mockResolvedValue({ reachable: true })
    const ok = await probeNow()
    expect(ok).toBe(true)
    expect(piStatus.value).toBe('reachable')
    expect(piLastOkAt.value).toBeTypeOf('number')
    expect(piProbing.value).toBe(false)
  })

  it('marks unreachable on failed probe', async () => {
    probeApiBase.mockResolvedValue({ reachable: false, reason: 'network' })
    const ok = await probeNow()
    expect(ok).toBe(false)
    expect(piStatus.value).toBe('unreachable')
    expect(piLastOkAt.value).toBeNull()
  })

  it('ensureReachable skips probe within warm window', async () => {
    probeApiBase.mockResolvedValue({ reachable: true })
    await probeNow()
    probeApiBase.mockClear()
    const ok = await ensureReachable()
    expect(ok).toBe(true)
    expect(probeApiBase).not.toHaveBeenCalled()
  })

  it('ensureReachable probes when warm window expired', async () => {
    probeApiBase.mockResolvedValue({ reachable: true })
    await probeNow()
    probeApiBase.mockClear()
    vi.advanceTimersByTime(WARM_WINDOW_MS + 1)
    probeApiBase.mockResolvedValue({ reachable: true })
    const ok = await ensureReachable()
    expect(ok).toBe(true)
    expect(probeApiBase).toHaveBeenCalledTimes(1)
  })

  it('ensureReachable force always probes', async () => {
    probeApiBase.mockResolvedValue({ reachable: true })
    await probeNow()
    probeApiBase.mockClear()
    probeApiBase.mockResolvedValue({ reachable: true })
    await ensureReachable({ force: true })
    expect(probeApiBase).toHaveBeenCalledTimes(1)
  })

  it('probes on resume when document becomes visible', async () => {
    let visibility: DocumentVisibilityState = 'hidden'
    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      get: () => visibility,
    })
    probeApiBase.mockResolvedValue({ reachable: true })

    const Comp = defineComponent({
      setup() {
        usePiConnectivityKeepalive()
        return () => null
      },
    })
    mount(Comp)
    await nextTick()
    expect(probeApiBase).not.toHaveBeenCalled()

    visibility = 'visible'
    document.dispatchEvent(new Event('visibilitychange'))
    await flushMicrotasks()
    expect(probeApiBase).toHaveBeenCalledTimes(1)
  })

  it('runs keepalive every 30s while visible and stops when hidden', async () => {
    let visibility: DocumentVisibilityState = 'visible'
    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      get: () => visibility,
    })
    probeApiBase.mockResolvedValue({ reachable: true })

    const Comp = defineComponent({
      setup() {
        usePiConnectivityKeepalive()
        return () => null
      },
    })
    const wrapper = mount(Comp)
    await flushMicrotasks()
    // Initial visible mount probes once.
    expect(probeApiBase).toHaveBeenCalledTimes(1)
    probeApiBase.mockClear()

    await vi.advanceTimersByTimeAsync(KEEPALIVE_MS)
    expect(probeApiBase).toHaveBeenCalledTimes(1)
    probeApiBase.mockClear()

    visibility = 'hidden'
    document.dispatchEvent(new Event('visibilitychange'))
    await flushMicrotasks()
    await vi.advanceTimersByTimeAsync(KEEPALIVE_MS * 2)
    expect(probeApiBase).not.toHaveBeenCalled()

    wrapper.unmount()
  })
})

async function flushMicrotasks() {
  await Promise.resolve()
  await Promise.resolve()
}
