import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { EdgeBundleEvent } from '@/types/api'

vi.mock('./pickPaymentType', () => ({
  pickPaymentType: vi.fn(),
}))

vi.mock('./cloudReachable', () => ({
  checkCloudReachable: vi.fn(),
}))

vi.mock('./sumupCheckout', () => ({
  collectSumupConnectedPayment: vi.fn(),
  cancelActiveSumupCheckout: vi.fn(),
  SUMUP_CANCELLED_MESSAGE: 'cancelled',
}))

import { pickPaymentType } from './pickPaymentType'
import { checkCloudReachable } from './cloudReachable'
import { collectSumupConnectedPayment } from './sumupCheckout'
import {
  resolvePaymentsForAmount,
  sumupPaymentFailureMessage,
  dismissSumupPaymentFailure,
} from './resolvePayment'

describe('resolvePaymentsForAmount sumup_connected', () => {
  const event = { id: 1, currency: 'CHF' } as EdgeBundleEvent

  beforeEach(() => {
    vi.mocked(pickPaymentType).mockReset()
    vi.mocked(checkCloudReachable).mockReset()
    vi.mocked(collectSumupConnectedPayment).mockReset()
    sumupPaymentFailureMessage.value = null
  })

  it('collects sumup connected payment via cloud checkout', async () => {
    vi.mocked(pickPaymentType).mockResolvedValue('sumup_connected')
    vi.mocked(checkCloudReachable).mockResolvedValue({ reachable: true, reason: null })
    vi.mocked(collectSumupConnectedPayment).mockResolvedValue({
      type: 'sumup_connected',
      amount_cents: 1200,
      sumup_transaction_id: 'txn_abc',
    })

    await expect(resolvePaymentsForAmount(event, 1200, 'order-9')).resolves.toEqual([
      {
        type: 'sumup_connected',
        amount_cents: 1200,
        sumup_transaction_id: 'txn_abc',
      },
    ])
    expect(collectSumupConnectedPayment).toHaveBeenCalledWith({
      event,
      amountCents: 1200,
      clientOrderId: 'order-9',
    })
  })

  it('throws when cloud is unreachable for sumup connected', async () => {
    vi.mocked(pickPaymentType).mockResolvedValue('sumup_connected')
    vi.mocked(checkCloudReachable).mockResolvedValue({ reachable: false, reason: null })
    await expect(resolvePaymentsForAmount(event, 500)).rejects.toThrow('Cloud-Verbindung erforderlich.')
  })

  it('calls onSumupShow then onSumupHide when collection fails', async () => {
    vi.mocked(pickPaymentType).mockResolvedValue('sumup_connected')
    vi.mocked(checkCloudReachable).mockResolvedValue({ reachable: true, reason: null })
    vi.mocked(collectSumupConnectedPayment).mockRejectedValue(new Error('fail'))
    const onSumupShow = vi.fn()
    const onSumupHide = vi.fn()
    await expect(
      resolvePaymentsForAmount(event, 800, null, { onSumupShow, onSumupHide }),
    ).rejects.toThrow('fail')
    expect(onSumupShow).toHaveBeenCalledWith({ amountCents: 800 })
    expect(onSumupHide).toHaveBeenCalledOnce()
  })

  it('does not call onSumupHide after successful collection', async () => {
    vi.mocked(pickPaymentType).mockResolvedValue('sumup_connected')
    vi.mocked(checkCloudReachable).mockResolvedValue({ reachable: true, reason: null })
    vi.mocked(collectSumupConnectedPayment).mockResolvedValue({
      type: 'sumup_connected',
      amount_cents: 800,
      sumup_transaction_id: 'txn',
    })
    const onSumupShow = vi.fn()
    const onSumupHide = vi.fn()
    await resolvePaymentsForAmount(event, 800, null, { onSumupShow, onSumupHide })
    expect(onSumupShow).toHaveBeenCalledOnce()
    expect(onSumupHide).not.toHaveBeenCalled()
  })

  it('sets sumupPaymentFailureMessage on collection failure', async () => {
    vi.mocked(pickPaymentType).mockResolvedValue('sumup_connected')
    vi.mocked(checkCloudReachable).mockResolvedValue({ reachable: true, reason: null })
    vi.mocked(collectSumupConnectedPayment).mockRejectedValue(new Error('Karte abgelehnt'))
    await expect(resolvePaymentsForAmount(event, 800)).rejects.toThrow('Karte abgelehnt')
    expect(sumupPaymentFailureMessage.value).toBe('Karte abgelehnt')
  })

  it('does not set failure message when operator cancels', async () => {
    vi.mocked(pickPaymentType).mockResolvedValue('sumup_connected')
    vi.mocked(checkCloudReachable).mockResolvedValue({ reachable: true, reason: null })
    vi.mocked(collectSumupConnectedPayment).mockRejectedValue(new Error('cancelled'))
    await expect(resolvePaymentsForAmount(event, 800)).rejects.toThrow('cancelled')
    expect(sumupPaymentFailureMessage.value).toBeNull()
  })

  it('calls onSumupHide when operator cancels', async () => {
    vi.mocked(pickPaymentType).mockResolvedValue('sumup_connected')
    vi.mocked(checkCloudReachable).mockResolvedValue({ reachable: true, reason: null })
    vi.mocked(collectSumupConnectedPayment).mockRejectedValue(new Error('cancelled'))
    const onSumupShow = vi.fn()
    const onSumupHide = vi.fn()
    await expect(
      resolvePaymentsForAmount(event, 800, null, { onSumupShow, onSumupHide }),
    ).rejects.toThrow('cancelled')
    expect(onSumupShow).toHaveBeenCalledOnce()
    expect(onSumupHide).toHaveBeenCalledOnce()
  })

  it('dismissSumupPaymentFailure clears the message', () => {
    sumupPaymentFailureMessage.value = 'Karte abgelehnt'
    dismissSumupPaymentFailure()
    expect(sumupPaymentFailureMessage.value).toBeNull()
  })
})
