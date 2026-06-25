import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { EdgeBundleEvent } from '@/types/api'

vi.mock('./stripeTerminalAvailability', () => ({
  stripeTerminalPickerEntry: vi.fn(async () => ({
    value: 'stripe_terminal',
    disabled: false,
  })),
}))

import {
  cancelPaymentType,
  cancelTwintQr,
  confirmPaymentType,
  confirmTwintQr,
  pickPaymentType,
  pickerOpen,
  twintQrOpen,
} from './pickPaymentType'

const cashEvent = {
  payment_types: ['cash'],
} as unknown as EdgeBundleEvent

const twintEvent = {
  payment_types: ['twint'],
  twint_qr_data_url: 'data:image/png;base64,abc',
} as unknown as EdgeBundleEvent

describe('pickPaymentType', () => {
  beforeEach(() => {
    pickerOpen.value = false
    twintQrOpen.value = false
  })

  it('auto-selects when only one enabled payment type', async () => {
    const type = await pickPaymentType(cashEvent, 500)
    expect(type).toBe('cash')
    expect(pickerOpen.value).toBe(false)
  })

  it('resolves from sheet confirm and cancel', async () => {
    const multiEvent = { payment_types: ['cash', 'sumup'] } as unknown as EdgeBundleEvent
    const pending = pickPaymentType(multiEvent, 1000)
    await vi.waitFor(() => expect(pickerOpen.value).toBe(true))
    confirmPaymentType('cash')
    await expect(pending).resolves.toBe('cash')

    const cancelled = pickPaymentType(multiEvent, 1000)
    await vi.waitFor(() => expect(pickerOpen.value).toBe(true))
    cancelPaymentType()
    await expect(cancelled).rejects.toThrow('cancelled')
  })

  it('shows TWINT QR hooks and resolves on confirm', async () => {
    const onTwintShow = vi.fn()
    const onTwintHide = vi.fn()
    const pending = pickPaymentType(twintEvent, 1200, { onTwintShow, onTwintHide })
    await vi.waitFor(() => expect(twintQrOpen.value).toBe(true))
    expect(onTwintShow).toHaveBeenCalledWith(
      expect.objectContaining({
        dataUrl: 'data:image/png;base64,abc',
        amountCents: 1200,
      }),
    )
    confirmTwintQr()
    await expect(pending).resolves.toBe('twint')
    expect(onTwintHide).toHaveBeenCalled()
  })

  it('rejects TWINT QR on cancel', async () => {
    const pending = pickPaymentType(twintEvent, 500)
    await vi.waitFor(() => expect(twintQrOpen.value).toBe(true))
    const assertion = expect(pending).rejects.toThrow('cancelled')
    cancelTwintQr()
    await assertion
  })
})
