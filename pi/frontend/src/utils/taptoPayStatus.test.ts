import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  checkTapToPayAdminStatus,
  resetTapToPayAdminStatusCacheForTests,
  tapToPayAdminStatusLabel,
} from './taptoPayStatus'

describe('checkTapToPayAdminStatus', () => {
  beforeEach(() => {
    resetTapToPayAdminStatusCacheForTests()
    delete window.AndroidTerminal
  })

  afterEach(() => {
    resetTapToPayAdminStatusCacheForTests()
    delete window.AndroidTerminal
  })

  it('returns unavailable when bridge/method missing', () => {
    expect(checkTapToPayAdminStatus()).toEqual({ code: 'unavailable' })
    window.AndroidTerminal = { collectPayment: vi.fn() }
    expect(checkTapToPayAdminStatus(true)).toEqual({ code: 'unavailable' })
  })

  it('maps ready from supported + code', () => {
    window.AndroidTerminal = {
      supportsTapToPay: () =>
        JSON.stringify({ ok: true, supported: true, code: 'ready', simulated: false }),
    }
    expect(checkTapToPayAdminStatus()).toEqual({ code: 'ready' })
  })

  it('maps ready_simulated', () => {
    window.AndroidTerminal = {
      supportsTapToPay: () =>
        JSON.stringify({ ok: true, supported: true, code: 'ready_simulated', simulated: true }),
    }
    expect(checkTapToPayAdminStatus()).toEqual({ code: 'ready_simulated' })
  })

  it('maps ready from supported when code absent (older APK)', () => {
    window.AndroidTerminal = {
      supportsTapToPay: () => JSON.stringify({ ok: true, supported: true }),
    }
    expect(checkTapToPayAdminStatus()).toEqual({ code: 'ready' })
  })

  it('maps location_missing from code', () => {
    window.AndroidTerminal = {
      supportsTapToPay: () =>
        JSON.stringify({
          ok: false,
          code: 'location_missing',
          error: 'Standortberechtigung für Kartenzahlung erforderlich.',
        }),
    }
    expect(checkTapToPayAdminStatus()).toEqual({ code: 'location_missing' })
  })

  it('maps location_missing from location error text (older APK)', () => {
    window.AndroidTerminal = {
      supportsTapToPay: () =>
        JSON.stringify({
          ok: false,
          error: 'Standortberechtigung für Kartenzahlung erforderlich.',
        }),
    }
    expect(checkTapToPayAdminStatus()).toEqual({ code: 'location_missing' })
  })

  it('maps unsupported', () => {
    window.AndroidTerminal = {
      supportsTapToPay: () =>
        JSON.stringify({
          ok: true,
          supported: false,
          code: 'unsupported',
          error: 'NFC missing',
        }),
    }
    expect(checkTapToPayAdminStatus()).toEqual({
      code: 'unsupported',
      detail: 'NFC missing',
    })
  })

  it('maps error for other failures', () => {
    window.AndroidTerminal = {
      supportsTapToPay: () =>
        JSON.stringify({ ok: false, error: 'init failed', code: 'error' }),
    }
    expect(checkTapToPayAdminStatus()).toEqual({
      code: 'error',
      detail: 'init failed',
    })
  })

  it('maps thrown bridge errors to error', () => {
    window.AndroidTerminal = {
      supportsTapToPay: () => {
        throw new Error('boom')
      },
    }
    expect(checkTapToPayAdminStatus()).toEqual({
      code: 'error',
      detail: 'boom',
    })
  })

  it('forces a fresh check when force=true', () => {
    const supportsTapToPay = vi
      .fn()
      .mockReturnValueOnce(JSON.stringify({ ok: true, supported: true, code: 'ready' }))
      .mockReturnValueOnce(
        JSON.stringify({ ok: false, code: 'location_missing', error: 'Standort' }),
      )
    window.AndroidTerminal = { supportsTapToPay }

    expect(checkTapToPayAdminStatus()).toEqual({ code: 'ready' })
    expect(checkTapToPayAdminStatus()).toEqual({ code: 'ready' })
    expect(supportsTapToPay).toHaveBeenCalledTimes(1)

    expect(checkTapToPayAdminStatus(true)).toEqual({ code: 'location_missing' })
    expect(supportsTapToPay).toHaveBeenCalledTimes(2)
  })
})

describe('tapToPayAdminStatusLabel', () => {
  it('returns German labels for each code', () => {
    expect(tapToPayAdminStatusLabel({ code: 'checking' })).toBe('prüfen…')
    expect(tapToPayAdminStatusLabel({ code: 'ready' })).toBe('bereit')
    expect(tapToPayAdminStatusLabel({ code: 'ready_simulated' })).toBe('bereit (simuliert)')
    expect(tapToPayAdminStatusLabel({ code: 'location_missing' })).toBe('Standort fehlt')
    expect(tapToPayAdminStatusLabel({ code: 'unsupported' })).toBe('nicht unterstützt')
    expect(tapToPayAdminStatusLabel({ code: 'error' })).toBe('Fehler')
    expect(tapToPayAdminStatusLabel({ code: 'unavailable' })).toBe('nicht verfügbar')
  })
})
