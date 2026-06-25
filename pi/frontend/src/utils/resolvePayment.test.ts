import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { EdgeBundleEvent } from '@/types/api'

vi.mock('./pickPaymentType', () => ({
  pickPaymentType: vi.fn(),
}))

vi.mock('./androidTerminal', () => ({
  collectTerminalPayment: vi.fn(),
}))

vi.mock('./stripeTerminalAvailability', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./stripeTerminalAvailability')>()
  return {
    ...actual,
    checkCloudReachable: vi.fn(),
    isStripeTerminalAndroidReady: vi.fn(),
  }
})

import { pickPaymentType } from './pickPaymentType'
import { collectTerminalPayment } from './androidTerminal'
import {
  checkCloudReachable,
  isStripeTerminalAndroidReady,
} from './stripeTerminalAvailability'
import { resolvePaymentsForAmount, terminalPaymentBusy } from './resolvePayment'

describe('resolvePaymentsForAmount', () => {
  const event = { id: 1, currency: 'CHF' } as EdgeBundleEvent

  beforeEach(() => {
    vi.mocked(pickPaymentType).mockReset()
    vi.mocked(collectTerminalPayment).mockReset()
    vi.mocked(checkCloudReachable).mockReset()
    vi.mocked(isStripeTerminalAndroidReady).mockReset()
    terminalPaymentBusy.value = false
  })

  it('returns buildPayment for non-terminal types', async () => {
    vi.mocked(pickPaymentType).mockResolvedValue('cash')
    await expect(resolvePaymentsForAmount(event, 500)).resolves.toEqual([
      { type: 'cash', amount_cents: 500 },
    ])
  })

  it('throws when stripe terminal prerequisites are missing', async () => {
    vi.mocked(pickPaymentType).mockResolvedValue('stripe_terminal')
    vi.mocked(isStripeTerminalAndroidReady).mockReturnValue(false)
    vi.mocked(checkCloudReachable).mockResolvedValue({ reachable: true, reason: null })
    await expect(resolvePaymentsForAmount(event, 500)).rejects.toThrow(
      'Nur in der Android-App verfügbar.',
    )
  })

  it('throws when cloud is unreachable for terminal payments', async () => {
    vi.mocked(pickPaymentType).mockResolvedValue('stripe_terminal')
    vi.mocked(isStripeTerminalAndroidReady).mockReturnValue(true)
    vi.mocked(checkCloudReachable).mockResolvedValue({ reachable: false, reason: null })
    await expect(resolvePaymentsForAmount(event, 500)).rejects.toThrow(
      'Cloud-Verbindung erforderlich.',
    )
  })

  it('collects terminal payment when prerequisites are met', async () => {
    vi.mocked(pickPaymentType).mockResolvedValue('stripe_terminal')
    vi.mocked(isStripeTerminalAndroidReady).mockReturnValue(true)
    vi.mocked(checkCloudReachable).mockResolvedValue({ reachable: true, reason: null })
    vi.mocked(collectTerminalPayment).mockResolvedValue({
      type: 'stripe_terminal',
      amount_cents: 800,
      stripe_payment_intent_id: 'pi_abc',
    })

    await expect(resolvePaymentsForAmount(event, 800, 'order-1')).resolves.toEqual([
      {
        type: 'stripe_terminal',
        amount_cents: 800,
        stripe_payment_intent_id: 'pi_abc',
      },
    ])
    expect(collectTerminalPayment).toHaveBeenCalledWith({
      eventId: 1,
      amountCents: 800,
      currency: 'CHF',
      clientOrderId: 'order-1',
    })
    expect(terminalPaymentBusy.value).toBe(false)
  })
})
