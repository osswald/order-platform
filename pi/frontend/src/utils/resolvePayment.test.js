import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./pickPaymentType', () => ({
  pickPaymentType: vi.fn(),
}))

vi.mock('./androidTerminal', () => ({
  collectTerminalPayment: vi.fn(),
}))

vi.mock('./stripeTerminalAvailability', async (importOriginal) => {
  const actual = await importOriginal()
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
  const event = { id: 1, currency: 'CHF' }

  beforeEach(() => {
    pickPaymentType.mockReset()
    collectTerminalPayment.mockReset()
    checkCloudReachable.mockReset()
    isStripeTerminalAndroidReady.mockReset()
    terminalPaymentBusy.value = false
  })

  it('returns buildPayment for non-terminal types', async () => {
    pickPaymentType.mockResolvedValue('cash')
    await expect(resolvePaymentsForAmount(event, 500)).resolves.toEqual([
      { type: 'cash', amount_cents: 500 },
    ])
  })

  it('throws when stripe terminal prerequisites are missing', async () => {
    pickPaymentType.mockResolvedValue('stripe_terminal')
    isStripeTerminalAndroidReady.mockReturnValue(false)
    checkCloudReachable.mockResolvedValue({ reachable: true })
    await expect(resolvePaymentsForAmount(event, 500)).rejects.toThrow(
      'Nur in der Android-App verfügbar.',
    )
  })

  it('collects terminal payment when prerequisites are met', async () => {
    pickPaymentType.mockResolvedValue('stripe_terminal')
    isStripeTerminalAndroidReady.mockReturnValue(true)
    checkCloudReachable.mockResolvedValue({ reachable: true })
    collectTerminalPayment.mockResolvedValue({ stripe_payment_intent_id: 'pi_abc' })

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
