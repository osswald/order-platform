import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api', () => ({
  api: vi.fn(),
  isAndroidApp: vi.fn(() => false),
}))

vi.mock('./androidTerminal', () => ({
  isAndroidTerminalAvailable: vi.fn(() => false),
}))

import { api } from '../api'
import { isAndroidTerminalAvailable } from './androidTerminal'
import {
  checkCloudReachable,
  isStripeTerminalAndroidReady,
  stripeTerminalDisabledHint,
  stripeTerminalPickerEntry,
} from './stripeTerminalAvailability'

describe('stripeTerminalDisabledHint', () => {
  it('returns German hints for missing prerequisites', () => {
    expect(stripeTerminalDisabledHint(false, true)).toBe('Nur in der Android-App verfügbar.')
    expect(stripeTerminalDisabledHint(true, false)).toBe('Cloud-Verbindung erforderlich.')
    expect(stripeTerminalDisabledHint(true, true)).toBeNull()
  })
})

describe('isStripeTerminalAndroidReady', () => {
  it('is true when terminal bridge or android app flag is available', () => {
    isAndroidTerminalAvailable.mockReturnValueOnce(true)
    expect(isStripeTerminalAndroidReady()).toBe(true)
  })
})

describe('checkCloudReachable', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-06-04T12:00:00Z'))
    api.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('probes cloud reachability via api', async () => {
    api.mockResolvedValue({ reachable: true, reason: null })
    await expect(checkCloudReachable(true)).resolves.toEqual({
      reachable: true,
      reason: null,
    })
    expect(api).toHaveBeenCalledWith('/v1/cloud/reachable')
  })

  it('caches probe results for 15 seconds', async () => {
    api.mockResolvedValue({ reachable: true, reason: null })
    await checkCloudReachable(true)
    await checkCloudReachable(false)
    expect(api).toHaveBeenCalledTimes(1)

    vi.advanceTimersByTime(16_000)
    api.mockResolvedValue({ reachable: false, reason: 'offline' })
    await checkCloudReachable(false)
    expect(api).toHaveBeenCalledTimes(2)
  })

  it('returns unreachable on api failure', async () => {
    api.mockRejectedValue(new Error('network'))
    await expect(checkCloudReachable(true)).resolves.toEqual({
      reachable: false,
      reason: 'probe_failed',
    })
  })
})

describe('stripeTerminalPickerEntry', () => {
  beforeEach(() => {
    api.mockReset()
    isAndroidTerminalAvailable.mockReturnValue(false)
  })

  it('disables entry when android is not ready', async () => {
    api.mockResolvedValue({ reachable: true })
    await expect(stripeTerminalPickerEntry()).resolves.toEqual({
      value: 'stripe_terminal',
      disabled: true,
      hint: 'Nur in der Android-App verfügbar.',
    })
  })
})
