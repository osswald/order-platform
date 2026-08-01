import { describe, expect, it } from 'vitest'
import type { EdgeBundleEvent } from '@/types/api'
import { pickPaymentType } from './pickPaymentType'

describe('pickPaymentType', () => {
  it('returns the only enabled payment type without opening the sheet', async () => {
    const event = { payment_types: ['cash'], currency: 'CHF' } as EdgeBundleEvent
    await expect(pickPaymentType(event, 500)).resolves.toBe('cash')
  })

  it('opens the picker when multiple types are enabled', async () => {
    const event = { payment_types: ['cash', 'twint'], currency: 'CHF' } as EdgeBundleEvent
    const pickPromise = pickPaymentType(event, 500)
    const { confirmPaymentType } = await import('./pickPaymentType')
    confirmPaymentType('twint')
    await expect(pickPromise).resolves.toBe('twint')
  })
})
