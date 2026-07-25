import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api', () => ({
  api: vi.fn(),
  isAndroidApp: vi.fn(() => false),
}))

vi.mock('./androidTerminal', () => ({
  isAndroidTerminalAvailable: vi.fn(() => false),
  checkTapToPayDeviceSupport: vi.fn(() => ({ status: 'unknown' })),
}))

import { api } from '@/api'
import { checkTapToPayDeviceSupport, isAndroidTerminalAvailable } from './androidTerminal'
import {
  checkCloudReachable,
  isStripeTerminalAndroidReady,
  stripeTerminalDisabledHint,
  stripeTerminalPickerEntry,
} from './stripeTerminalAvailability'
import type { TapToPaySupportStatus } from './androidTerminal'

describe('stripeTerminalDisabledHint', () => {
  const supported: TapToPaySupportStatus = { status: 'supported' }

  it('returns German hints for missing prerequisites', () => {
    expect(stripeTerminalDisabledHint(false, true, supported)).toBe(
      'Nur in der Android-App verfügbar.',
    )
    expect(stripeTerminalDisabledHint(true, false, supported)).toBe(
      'Cloud-Verbindung erforderlich.',
    )
    expect(stripeTerminalDisabledHint(true, true, supported)).toBeNull()
  })

  it('prioritizes android and cloud over device support', () => {
    expect(
      stripeTerminalDisabledHint(false, false, { status: 'unsupported' }),
    ).toBe('Nur in der Android-App verfügbar.')
    expect(
      stripeTerminalDisabledHint(true, false, { status: 'unsupported' }),
    ).toBe('Cloud-Verbindung erforderlich.')
  })

  it('disables with device hint when unsupported', () => {
    expect(
      stripeTerminalDisabledHint(true, true, { status: 'unsupported', error: 'no nfc' }),
    ).toBe('Gerät unterstützt keine Kartenzahlung (Tap to Pay).')
  })

  it('disables with location hint when support check fails', () => {
    expect(
      stripeTerminalDisabledHint(true, true, {
        status: 'check_failed',
        error: 'Standortberechtigung für Kartenzahlung erforderlich.',
      }),
    ).toBe('Standortberechtigung für Kartenzahlung erforderlich.')
  })

  it('does not disable for unknown device support (older APK)', () => {
    expect(stripeTerminalDisabledHint(true, true, { status: 'unknown' })).toBeNull()
  })
})

describe('isStripeTerminalAndroidReady', () => {
  it('is true when terminal bridge or android app flag is available', () => {
    vi.mocked(isAndroidTerminalAvailable).mockReturnValueOnce(true)
    expect(isStripeTerminalAndroidReady()).toBe(true)
  })
})

describe('checkCloudReachable', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-06-04T12:00:00Z'))
    vi.mocked(api).mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('probes cloud reachability via api', async () => {
    vi.mocked(api).mockResolvedValue({ reachable: true, reason: null })
    await expect(checkCloudReachable(true)).resolves.toEqual({
      reachable: true,
      reason: null,
    })
    expect(api).toHaveBeenCalledWith('/v1/cloud/reachable')
  })

  it('caches probe results for 15 seconds', async () => {
    vi.mocked(api).mockResolvedValue({ reachable: true, reason: null })
    await checkCloudReachable(true)
    await checkCloudReachable(false)
    expect(api).toHaveBeenCalledTimes(1)

    vi.advanceTimersByTime(16_000)
    vi.mocked(api).mockResolvedValue({ reachable: false, reason: 'offline' })
    await checkCloudReachable(false)
    expect(api).toHaveBeenCalledTimes(2)
  })

  it('returns unreachable on api failure', async () => {
    vi.mocked(api).mockRejectedValue(new Error('network'))
    await expect(checkCloudReachable(true)).resolves.toEqual({
      reachable: false,
      reason: 'probe_failed',
    })
  })
})

describe('stripeTerminalPickerEntry', () => {
  beforeEach(() => {
    vi.mocked(api).mockReset()
    vi.mocked(isAndroidTerminalAvailable).mockReturnValue(false)
    vi.mocked(checkTapToPayDeviceSupport).mockReturnValue({ status: 'unknown' })
  })

  it('disables entry when android is not ready', async () => {
    vi.mocked(api).mockResolvedValue({ reachable: true })
    await expect(stripeTerminalPickerEntry()).resolves.toEqual({
      value: 'stripe_terminal',
      disabled: true,
      hint: 'Nur in der Android-App verfügbar.',
    })
  })

  it('disables entry when device does not support Tap to Pay', async () => {
    vi.mocked(isAndroidTerminalAvailable).mockReturnValue(true)
    vi.mocked(api).mockResolvedValue({ reachable: true })
    vi.mocked(checkTapToPayDeviceSupport).mockReturnValue({ status: 'unsupported' })
    await expect(stripeTerminalPickerEntry()).resolves.toEqual({
      value: 'stripe_terminal',
      disabled: true,
      hint: 'Gerät unterstützt keine Kartenzahlung (Tap to Pay).',
    })
  })

  it('enables entry when android, cloud, and device support are ready', async () => {
    vi.mocked(isAndroidTerminalAvailable).mockReturnValue(true)
    vi.mocked(api).mockResolvedValue({ reachable: true })
    vi.mocked(checkTapToPayDeviceSupport).mockReturnValue({ status: 'supported' })
    await expect(stripeTerminalPickerEntry()).resolves.toEqual({
      value: 'stripe_terminal',
      disabled: false,
      hint: undefined,
    })
  })

  it('keeps entry enabled for older APK without supportsTapToPay', async () => {
    vi.mocked(isAndroidTerminalAvailable).mockReturnValue(true)
    vi.mocked(api).mockResolvedValue({ reachable: true })
    vi.mocked(checkTapToPayDeviceSupport).mockReturnValue({ status: 'unknown' })
    await expect(stripeTerminalPickerEntry()).resolves.toEqual({
      value: 'stripe_terminal',
      disabled: false,
      hint: undefined,
    })
  })
})
