import { describe, expect, it } from 'vitest'
import type { EdgeBundleEvent } from '@/types/api'
import {
  buildPayment,
  buildSumupConnectedPayment,
  eventPaymentTypes,
  eventTwintQrDataUrl,
  paymentTypeLabel,
} from './paymentTypes'

describe('paymentTypeLabel', () => {
  it('maps known payment types', () => {
    expect(paymentTypeLabel('cash')).toBe('Bargeld')
    expect(paymentTypeLabel('sumup')).toBe('Sumup (manual)')
    expect(paymentTypeLabel('sumup_connected')).toBe('Sumup connected')
    expect(paymentTypeLabel('stripe_terminal')).toBe('Karte')
    expect(paymentTypeLabel('unknown')).toBe('unknown')
  })
})

describe('eventPaymentTypes', () => {
  it('orders types according to PAYMENT_TYPE_ORDER', () => {
    expect(
      eventPaymentTypes({
        payment_types: ['twint', 'cash', 'sumup', 'sumup_connected'],
      } as EdgeBundleEvent),
    ).toEqual(['cash', 'twint', 'sumup', 'sumup_connected'])
  })

  it('defaults to cash when missing', () => {
    expect(eventPaymentTypes(null)).toEqual(['cash'])
  })

  it('ignores deactivated stripe_terminal in event config', () => {
    expect(
      eventPaymentTypes({ payment_types: ['cash', 'stripe_terminal'] } as EdgeBundleEvent),
    ).toEqual(['cash'])
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

describe('buildSumupConnectedPayment', () => {
  it('includes sumup transaction id', () => {
    expect(buildSumupConnectedPayment(1500, 'txn_abc')).toEqual([
      {
        type: 'sumup_connected',
        amount_cents: 1500,
        sumup_transaction_id: 'txn_abc',
      },
    ])
  })
})
