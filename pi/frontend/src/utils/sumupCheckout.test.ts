import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.fn()

vi.mock('@/api', () => ({
  api: (...args: unknown[]) => api(...args),
}))

vi.mock('@/store/sessions', () => ({
  waiter: { value: null as { uuid: string; name: string } | null },
  registerSession: { value: null },
}))

import { waiter } from '@/store/sessions'
import { createSumupCheckout } from './sumupCheckout'

describe('createSumupCheckout waiter_uuid', () => {
  beforeEach(() => {
    api.mockReset()
    api.mockResolvedValue({ checkout_id: 'co_1', status: 'pending' })
    waiter.value = null
  })

  it('sends waiter_uuid when a waiter session exists', async () => {
    waiter.value = { uuid: 'w-1', name: 'Anna' }
    await createSumupCheckout({
      eventId: 11,
      amountCents: 500,
      currency: 'CHF',
      readerId: 'rdr_1',
      clientOrderId: 'order-1',
    })
    expect(api).toHaveBeenCalledOnce()
    const body = JSON.parse((api.mock.calls[0][1] as RequestInit).body as string)
    expect(body.waiter_uuid).toBe('w-1')
    expect(body.client_order_id).toBe('order-1')
  })

  it('omits waiter_uuid when no waiter session', async () => {
    await createSumupCheckout({
      eventId: 11,
      amountCents: 500,
      currency: 'CHF',
      readerId: 'rdr_1',
    })
    const body = JSON.parse((api.mock.calls[0][1] as RequestInit).body as string)
    expect(body.waiter_uuid).toBeUndefined()
  })
})
