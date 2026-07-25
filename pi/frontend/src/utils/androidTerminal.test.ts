import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  checkTapToPayDeviceSupport,
  isAndroidTerminalAvailable,
  resetTapToPaySupportCacheForTests,
} from './androidTerminal'

describe('isAndroidTerminalAvailable', () => {
  afterEach(() => {
    delete window.AndroidTerminal
  })

  it('is true when AndroidTerminal bridge is present', () => {
    window.AndroidTerminal = { collectPayment: vi.fn() }
    expect(isAndroidTerminalAvailable()).toBe(true)
  })

  it('is false when bridge is missing', () => {
    expect(isAndroidTerminalAvailable()).toBe(false)
  })
})

describe('checkTapToPayDeviceSupport', () => {
  beforeEach(() => {
    resetTapToPaySupportCacheForTests()
    delete window.AndroidTerminal
  })

  afterEach(() => {
    resetTapToPaySupportCacheForTests()
    delete window.AndroidTerminal
  })

  it('returns unknown when supportsTapToPay is missing (older APK)', () => {
    window.AndroidTerminal = { collectPayment: vi.fn() }
    expect(checkTapToPayDeviceSupport()).toEqual({ status: 'unknown' })
  })

  it('returns unknown when bridge is absent', () => {
    expect(checkTapToPayDeviceSupport()).toEqual({ status: 'unknown' })
  })

  it('parses supported: true', () => {
    window.AndroidTerminal = {
      supportsTapToPay: () => JSON.stringify({ ok: true, supported: true }),
    }
    expect(checkTapToPayDeviceSupport()).toEqual({ status: 'supported' })
  })

  it('parses supported: false with optional error', () => {
    window.AndroidTerminal = {
      supportsTapToPay: () =>
        JSON.stringify({ ok: true, supported: false, error: 'NFC missing' }),
    }
    expect(checkTapToPayDeviceSupport()).toEqual({
      status: 'unsupported',
      error: 'NFC missing',
    })
  })

  it('maps ok: false to check_failed', () => {
    window.AndroidTerminal = {
      supportsTapToPay: () =>
        JSON.stringify({
          ok: false,
          error: 'Standortberechtigung für Kartenzahlung erforderlich.',
        }),
    }
    expect(checkTapToPayDeviceSupport()).toEqual({
      status: 'check_failed',
      error: 'Standortberechtigung für Kartenzahlung erforderlich.',
    })
  })

  it('caches the result until reset or force', () => {
    const supportsTapToPay = vi
      .fn()
      .mockReturnValueOnce(JSON.stringify({ ok: true, supported: true }))
      .mockReturnValueOnce(JSON.stringify({ ok: true, supported: false }))
    window.AndroidTerminal = { supportsTapToPay }

    expect(checkTapToPayDeviceSupport()).toEqual({ status: 'supported' })
    expect(checkTapToPayDeviceSupport()).toEqual({ status: 'supported' })
    expect(supportsTapToPay).toHaveBeenCalledTimes(1)

    expect(checkTapToPayDeviceSupport(true)).toEqual({ status: 'unsupported', error: null })
    expect(supportsTapToPay).toHaveBeenCalledTimes(2)
  })
})
