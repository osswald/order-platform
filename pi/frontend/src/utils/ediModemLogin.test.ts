import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { isAndroidApp } from '@/api'
import {
  MODEM_HANDSHAKE_EVENT,
  awaitAndroidModemHandshake,
  isEdiWaiterName,
  shouldRunEdiModemHandshake,
} from './ediModemLogin'

vi.mock('@/api', () => ({
  isAndroidApp: vi.fn(() => false),
}))

describe('isEdiWaiterName', () => {
  it('matches edi case-insensitively with trim', () => {
    expect(isEdiWaiterName('edi')).toBe(true)
    expect(isEdiWaiterName('Edi')).toBe(true)
    expect(isEdiWaiterName(' EDI ')).toBe(true)
    expect(isEdiWaiterName('Edith')).toBe(false)
    expect(isEdiWaiterName('')).toBe(false)
    expect(isEdiWaiterName(null)).toBe(false)
  })
})

describe('shouldRunEdiModemHandshake', () => {
  afterEach(() => {
    vi.mocked(isAndroidApp).mockReturnValue(false)
  })

  it('runs only on Android for edi', () => {
    vi.mocked(isAndroidApp).mockReturnValue(true)
    expect(shouldRunEdiModemHandshake('Edi')).toBe(true)
    expect(shouldRunEdiModemHandshake('Anna')).toBe(false)
  })

  it('skips on non-Android even for edi', () => {
    vi.mocked(isAndroidApp).mockReturnValue(false)
    expect(shouldRunEdiModemHandshake('edi')).toBe(false)
  })
})

describe('awaitAndroidModemHandshake', () => {
  beforeEach(() => {
    delete window.AndroidApp
  })

  afterEach(() => {
    delete window.AndroidApp
    vi.useRealTimers()
  })

  it('soft-fails when bridge method is missing', async () => {
    await expect(awaitAndroidModemHandshake(50)).resolves.toBe(false)
  })

  it('resolves true when native event reports ok', async () => {
    window.AndroidApp = {
      playModemHandshake: () => {
        window.dispatchEvent(
          new CustomEvent(MODEM_HANDSHAKE_EVENT, { detail: { ok: true } }),
        )
      },
    }
    await expect(awaitAndroidModemHandshake(1000)).resolves.toBe(true)
  })

  it('resolves false on soft-fail event so login can continue', async () => {
    window.AndroidApp = {
      playModemHandshake: () => {
        window.dispatchEvent(
          new CustomEvent(MODEM_HANDSHAKE_EVENT, { detail: { ok: false } }),
        )
      },
    }
    await expect(awaitAndroidModemHandshake(1000)).resolves.toBe(false)
  })

  it('soft-fails on timeout', async () => {
    vi.useFakeTimers()
    window.AndroidApp = {
      playModemHandshake: () => {
        /* never fires event */
      },
    }
    const pending = awaitAndroidModemHandshake(5000)
    await vi.advanceTimersByTimeAsync(5000)
    await expect(pending).resolves.toBe(false)
  })
})
