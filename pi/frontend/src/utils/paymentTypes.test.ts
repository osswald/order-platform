import { describe, expect, it } from 'vitest'
import type { EdgeBundleEvent } from '@/types/api'
import {
  buildPayment,
  buildStripeTerminalPayment,
  eventPaymentTypes,
  eventTwintQrDataUrl,
  paymentTypeLabel,
} from './paymentTypes'

describe('paymentTypeLabel', () => {
  it('maps known payment types', () => {
    expect(paymentTypeLabel('cash')).toBe('Bargeld')
    expect(paymentTypeLabel('stripe_terminal')).toBe('Karte')
    expect(paymentTypeLabel('unknown')).toBe('unknown')
  })
})

describe('eventPaymentTypes', () => {
  it('orders types according to PAYMENT_TYPE_ORDER', () => {
    expect(eventPaymentTypes({ payment_types: ['twint', 'cash', 'sumup'] } as EdgeBundleEvent)).toEqual([
      'cash',
      'twint',
      'sumup',
    ])
  })

  it('defaults to cash when missing', () => {
    expect(eventPaymentTypes(null)).toEqual(['cash'])
  })
})

describe('eventTwintQrDataUrl', () => {
  it('accepts data URLs only', () => {
    expect(eventTwintQrDataUrl({ twint_qr_data_url: 'data:image/png;base64,abc' } as EdgeBundleEvent)).toBe(
      'data:image/png;base64,abc',
    )
    expect(eventTwintQrDataUrl({ twint_qr_data_url: 'https://example.com/x' } as EdgeBundleEvent)).toBeNull()
  })
})

describe('buildPayment', () => {
  it('returns a single payment row with non-negative cents', () => {
    expect(buildPayment(500, 'cash')).toEqual([{ type: 'cash', amount_cents: 500 }])
    expect(buildPayment(-10, 'twint')).toEqual([{ type: 'twint', amount_cents: 0 }])
  })
})

describe('buildStripeTerminalPayment', () => {
  it('includes stripe payment intent id', () => {
    expect(buildStripeTerminalPayment(1200, 'pi_123')).toEqual([
      {
        type: 'stripe_terminal',
        amount_cents: 1200,
        stripe_payment_intent_id: 'pi_123',
      },
    ])
  })
})
