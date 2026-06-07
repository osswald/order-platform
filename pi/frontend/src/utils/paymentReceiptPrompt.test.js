import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api', () => ({
  api: vi.fn(),
  isAndroidApp: vi.fn(() => false),
}))

vi.mock('./androidPrinter', () => ({
  isBluetoothPrinterConfigured: vi.fn(() => false),
  printPaymentReceipt: vi.fn(),
}))

import { api } from '../api'
import {
  confirmReceiptPrintYes,
  offerPaymentReceipt,
  receiptPromptOpen,
} from './paymentReceiptPrompt'

describe('offerPaymentReceipt preferredTargetUuid', () => {
  const event = {
    offer_payment_receipt: true,
    printer_hosts: {
      'st-bar': '10.0.0.1:9100',
      'reg-1': '10.0.0.2:9100',
    },
    configuration: {
      stations: [{ uuid: 'st-bar', name: 'Bar' }],
      cash_registers: [{ uuid: 'reg-1', name: 'Front' }],
    },
  }

  beforeEach(() => {
    api.mockReset()
    api.mockResolvedValue({ print_job_id: 1 })
    receiptPromptOpen.value = false
  })

  it('prints to preferred register without station picker', async () => {
    const showToast = vi.fn()
    const promise = offerPaymentReceipt({
      paymentId: 42,
      event,
      showToast,
      preferredTargetUuid: 'reg-1',
    })
    confirmReceiptPrintYes()
    await promise

    expect(api).toHaveBeenCalledWith('/v1/payments/42/receipt/print', {
      method: 'POST',
      body: JSON.stringify({ station_uuid: 'reg-1' }),
    })
    expect(showToast).toHaveBeenCalledWith('Beleg an Drucker gesendet.', 'ok')
  })
})
