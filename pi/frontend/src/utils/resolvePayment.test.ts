import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { EdgeBundleEvent } from '@/types/api'

vi.mock('./pickPaymentType', () => ({
  pickPaymentType: vi.fn(),
}))

vi.mock('./cloudReachable', () => ({
  checkCloudReachable: vi.fn(),
}))

import { pickPaymentType } from './pickPaymentType'
import { checkCloudReachable } from './cloudReachable'
import { resolvePaymentsForAmount, terminalPaymentBusy } from './resolvePayment'

describe('resolvePaymentsForAmount', () => {
  const event = { id: 1, currency: 'CHF' } as EdgeBundleEvent

  beforeEach(() => {
    vi.mocked(pickPaymentType).mockReset()
    vi.mocked(checkCloudReachable).mockReset()
    terminalPaymentBusy.value = false
  })

  it('returns buildPayment for non-cloud types', async () => {
    vi.mocked(pickPaymentType).mockResolvedValue('cash')
    await expect(resolvePaymentsForAmount(event, 500)).resolves.toEqual([
      { type: 'cash', amount_cents: 500 },
    ])
  })
})
