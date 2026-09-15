import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { EdgeBundleEvent } from '@/types/api'

const api = vi.fn()

vi.mock('@/api', () => ({
  api: (...args: unknown[]) => api(...args),
}))

vi.mock('@/store/sessions', () => ({
  waiter: { value: null as { uuid: string; name: string; sumupReaderId?: string } | null },
  registerSession: { value: null },
}))

vi.mock('@/store/bundle', () => ({
  bundle: {
    value: {
      sumup_readers: [{ sumup_reader_id: 'rdr_1', label: 'Solo 1' }],
    },
  },
}))

import { waiter } from '@/store/sessions'
import {
  cancelActiveSumupCheckout,
  collectSumupConnectedPayment,
  createSumupCheckout,
  SUMUP_CANCELLED_MESSAGE,
} from './sumupCheckout'

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

describe('collectSumupConnectedPayment cancel and failure', () => {
  const event = {
    id: 11,
    currency: 'CHF',
  } as EdgeBundleEvent

  beforeEach(() => {
    api.mockReset()
    waiter.value = null
    vi.useRealTimers()
  })

  it('cancels during poll, terminates reader, and does not return a payment', async () => {
    vi.useFakeTimers()
    api.mockImplementation(async (path: string) => {
      if (String(path).includes('/checkout') && !String(path).includes('status')) {
        return { checkout_id: 'co_cancel', status: 'pending' }
      }
      if (String(path).includes('/status')) {
        return { checkout_id: 'co_cancel', status: 'pending' }
      }
      if (String(path).includes('/terminate')) {
        return { ok: true }
      }
      throw new Error(`unexpected path ${path}`)
    })

    const collection = collectSumupConnectedPayment({ event, amountCents: 900 })
    const expectRejected = expect(collection).rejects.toThrow(SUMUP_CANCELLED_MESSAGE)

    // Allow create checkout to finish, then cancel while status is pending.
    await vi.advanceTimersByTimeAsync(0)
    await Promise.resolve()
    await Promise.resolve()
    cancelActiveSumupCheckout()
    await vi.advanceTimersByTimeAsync(2000)
    await expectRejected

    const terminateCalls = api.mock.calls.filter((c) => String(c[0]).includes('/terminate'))
    expect(terminateCalls.length).toBeGreaterThanOrEqual(1)
    const terminateBody = JSON.parse((terminateCalls[0][1] as RequestInit).body as string)
    expect(terminateBody.reader_id).toBe('rdr_1')
    expect(terminateBody.event_id).toBe(11)
  })

  it('terminates on failed status and does not return a payment', async () => {
    api.mockImplementation(async (path: string) => {
      if (String(path).includes('/checkout') && !String(path).includes('status')) {
        return { checkout_id: 'co_fail', status: 'pending' }
      }
      if (String(path).includes('/status')) {
        return { checkout_id: 'co_fail', status: 'failed' }
      }
      if (String(path).includes('/terminate')) {
        return { ok: true }
      }
      throw new Error(`unexpected path ${path}`)
    })

    await expect(collectSumupConnectedPayment({ event, amountCents: 500 })).rejects.toThrow(
      'SumUp-Zahlung fehlgeschlagen oder abgebrochen.',
    )
    const terminateCalls = api.mock.calls.filter((c) => String(c[0]).includes('/terminate'))
    expect(terminateCalls).toHaveLength(1)
  })

  it('terminates on timeout and does not return a payment', async () => {
    vi.useFakeTimers()
    api.mockImplementation(async (path: string) => {
      if (String(path).includes('/checkout') && !String(path).includes('status')) {
        return { checkout_id: 'co_timeout', status: 'pending' }
      }
      if (String(path).includes('/status')) {
        return { checkout_id: 'co_timeout', status: 'pending' }
      }
      if (String(path).includes('/terminate')) {
        return { ok: true }
      }
      throw new Error(`unexpected path ${path}`)
    })

    const collection = collectSumupConnectedPayment({ event, amountCents: 500 })
    const expectRejected = expect(collection).rejects.toThrow('SumUp-Zahlung: Zeitüberschreitung.')
    await vi.advanceTimersByTimeAsync(120_000 + 2000)
    await expectRejected
    const terminateCalls = api.mock.calls.filter((c) => String(c[0]).includes('/terminate'))
    expect(terminateCalls.length).toBeGreaterThanOrEqual(1)
  })
})
