import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { isAndroidApp } from '@/api'
import {
  MODEM_HANDSHAKE_EVENT,
  awaitAndroidModemHandshake,
  blurActiveInput,
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

describe('blurActiveInput', () => {
  it('blurs the active element when it is an HTMLElement', () => {
    const input = document.createElement('input')
    document.body.appendChild(input)
    input.focus()
    expect(document.activeElement).toBe(input)
    blurActiveInput()
    expect(document.activeElement).not.toBe(input)
    input.remove()
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

  it('blurs the active input before starting the handshake', async () => {
    const input = document.createElement('input')
    document.body.appendChild(input)
    input.focus()
    window.AndroidApp = {
      playModemHandshake: () => {
        window.dispatchEvent(
          new CustomEvent(MODEM_HANDSHAKE_EVENT, { detail: { ok: true } }),
        )
      },
    }
    await awaitAndroidModemHandshake(1000)
    expect(document.activeElement).not.toBe(input)
    input.remove()
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

  it('invokes playModemHandshake on the bridge object (Android WebView this-binding)', async () => {
    const bridge = {
      playModemHandshake(this: unknown) {
        if (this !== bridge) {
          throw new Error("Java bridge method can't be invoked on a non-injected object")
        }
        window.dispatchEvent(
          new CustomEvent(MODEM_HANDSHAKE_EVENT, { detail: { ok: true } }),
        )
      },
    }
    window.AndroidApp = bridge
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
