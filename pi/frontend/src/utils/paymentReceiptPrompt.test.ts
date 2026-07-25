import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { EdgeBundleEvent } from '@/types/api'

vi.mock('../api', () => ({
  api: vi.fn(),
  isAndroidApp: vi.fn(() => false),
}))

vi.mock('./androidPrinter', () => ({
  isBluetoothPrinterConfigured: vi.fn(() => false),
  checkBluetoothPrinterReachability: vi.fn(() => 'unreachable'),
  printPaymentReceipt: vi.fn(),
}))

import { api, isAndroidApp } from '@/api'
import {
  checkBluetoothPrinterReachability,
  isBluetoothPrinterConfigured,
  printPaymentReceipt,
} from './androidPrinter'
import {
  bluetoothPrintingEnabled,
  cancelReceiptPrompt,
  confirmReceiptPrintNo,
  confirmReceiptPrintYes,
  offerPaymentReceipt,
  offerPaymentReceiptAfterSettle,
  offerPaymentReceiptEnabled,
  receiptPromptOpen,
  resolveBluetoothPrintGate,
  selectReceiptStation,
} from './paymentReceiptPrompt'

describe('offerPaymentReceiptEnabled', () => {
  it('returns false when event disables receipts', () => {
    expect(offerPaymentReceiptEnabled({ offer_payment_receipt: false } as unknown as EdgeBundleEvent)).toBe(false)
    expect(offerPaymentReceiptEnabled({ offer_payment_receipt: true } as unknown as EdgeBundleEvent)).toBe(true)
  })
})

describe('bluetoothPrintingEnabled', () => {
  it('is off by default and on when event enables Bluetooth', () => {
    expect(bluetoothPrintingEnabled(null)).toBe(false)
    expect(bluetoothPrintingEnabled({} as unknown as EdgeBundleEvent)).toBe(false)
    expect(
      bluetoothPrintingEnabled({ bluetooth_printing_enabled: false } as unknown as EdgeBundleEvent),
    ).toBe(false)
    expect(
      bluetoothPrintingEnabled({ bluetooth_printing_enabled: true } as unknown as EdgeBundleEvent),
    ).toBe(true)
  })
})

describe('resolveBluetoothPrintGate', () => {
  beforeEach(() => {
    vi.mocked(isAndroidApp).mockReturnValue(false)
    vi.mocked(isBluetoothPrinterConfigured).mockReturnValue(false)
    vi.mocked(checkBluetoothPrinterReachability).mockReturnValue('unreachable')
  })

  it('skips when not Android / not configured / flag off', () => {
    expect(
      resolveBluetoothPrintGate({ bluetooth_printing_enabled: true } as unknown as EdgeBundleEvent),
    ).toBe('skip')
    vi.mocked(isAndroidApp).mockReturnValue(true)
    vi.mocked(isBluetoothPrinterConfigured).mockReturnValue(true)
    expect(
      resolveBluetoothPrintGate({ bluetooth_printing_enabled: false } as unknown as EdgeBundleEvent),
    ).toBe('skip')
  })

  it('uses Bluetooth when probe reports reachable', () => {
    vi.mocked(isAndroidApp).mockReturnValue(true)
    vi.mocked(isBluetoothPrinterConfigured).mockReturnValue(true)
    vi.mocked(checkBluetoothPrinterReachability).mockReturnValue('reachable')
    expect(
      resolveBluetoothPrintGate({ bluetooth_printing_enabled: true } as unknown as EdgeBundleEvent),
    ).toBe('use')
  })

  it('tries Bluetooth on older APK without probe', () => {
    vi.mocked(isAndroidApp).mockReturnValue(true)
    vi.mocked(isBluetoothPrinterConfigured).mockReturnValue(true)
    vi.mocked(checkBluetoothPrinterReachability).mockReturnValue('unknown')
    expect(
      resolveBluetoothPrintGate({ bluetooth_printing_enabled: true } as unknown as EdgeBundleEvent),
    ).toBe('try')
  })

  it('skips when probe reports unreachable', () => {
    vi.mocked(isAndroidApp).mockReturnValue(true)
    vi.mocked(isBluetoothPrinterConfigured).mockReturnValue(true)
    vi.mocked(checkBluetoothPrinterReachability).mockReturnValue('unreachable')
    expect(
      resolveBluetoothPrintGate({ bluetooth_printing_enabled: true } as unknown as EdgeBundleEvent),
    ).toBe('skip')
  })
})

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
  } as unknown as EdgeBundleEvent

  beforeEach(() => {
    vi.mocked(api).mockReset()
    vi.mocked(api).mockResolvedValue({ print_job_id: 1 })
    vi.mocked(isAndroidApp).mockReturnValue(false)
    vi.mocked(isBluetoothPrinterConfigured).mockReturnValue(false)
    vi.mocked(checkBluetoothPrinterReachability).mockReturnValue('unreachable')
    vi.mocked(printPaymentReceipt).mockReset()
    vi.mocked(printPaymentReceipt).mockResolvedValue({ ok: true })
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

  it('skips printing when user declines', async () => {
    const showToast = vi.fn()
    const promise = offerPaymentReceipt({ paymentId: 1, event, showToast })
    confirmReceiptPrintNo()
    await promise
    expect(api).not.toHaveBeenCalled()
  })

  it('picks station when multiple targets exist', async () => {
    const showToast = vi.fn()
    const promise = offerPaymentReceipt({ paymentId: 7, event, showToast })
    confirmReceiptPrintYes()
    await Promise.resolve()
    selectReceiptStation('st-bar')
    await promise
    expect(api).toHaveBeenCalledWith('/v1/payments/7/receipt/print', {
      method: 'POST',
      body: JSON.stringify({ station_uuid: 'st-bar' }),
    })
  })

  it('aborts when prompt is cancelled', async () => {
    const promise = offerPaymentReceipt({ paymentId: 3, event })
    cancelReceiptPrompt()
    await expect(promise).resolves.toBeUndefined()
    expect(api).not.toHaveBeenCalled()
  })

  it('reports missing printer targets', async () => {
    const showToast = vi.fn()
    const bareEvent = { offer_payment_receipt: true, configuration: {} } as unknown as EdgeBundleEvent
    const promise = offerPaymentReceipt({ paymentId: 9, event: bareEvent, showToast })
    confirmReceiptPrintYes()
    await promise
    expect(showToast).toHaveBeenCalledWith('Kein Drucker konfiguriert.', 'err')
  })

  it('prints to sole configured target without station picker', async () => {
    const singleTargetEvent = {
      offer_payment_receipt: true,
      printer_hosts: { 'st-only': '10.0.0.9:9100' },
      configuration: { stations: [{ uuid: 'st-only', name: 'Only' }] },
    } as unknown as EdgeBundleEvent
    const showToast = vi.fn()
    const promise = offerPaymentReceipt({ paymentId: 11, event: singleTargetEvent, showToast })
    confirmReceiptPrintYes()
    await promise
    expect(api).toHaveBeenCalledWith('/v1/payments/11/receipt/print', {
      method: 'POST',
      body: JSON.stringify({ station_uuid: 'st-only' }),
    })
  })

  it('uses Bluetooth when event enables it and printer is reachable', async () => {
    vi.mocked(isAndroidApp).mockReturnValue(true)
    vi.mocked(isBluetoothPrinterConfigured).mockReturnValue(true)
    vi.mocked(checkBluetoothPrinterReachability).mockReturnValue('reachable')
    vi.mocked(printPaymentReceipt).mockResolvedValue({ ok: true })
    const btEvent = {
      ...event,
      bluetooth_printing_enabled: true,
    } as unknown as EdgeBundleEvent
    const showToast = vi.fn()
    const promise = offerPaymentReceipt({ paymentId: 55, event: btEvent, showToast })
    confirmReceiptPrintYes()
    await promise
    expect(printPaymentReceipt).toHaveBeenCalledWith(55, { reprint: false })
    expect(api).not.toHaveBeenCalled()
    expect(showToast).toHaveBeenCalledWith('Beleg gedruckt.', 'ok')
  })

  it('falls back to stations when Bluetooth is configured but unreachable', async () => {
    vi.mocked(isAndroidApp).mockReturnValue(true)
    vi.mocked(isBluetoothPrinterConfigured).mockReturnValue(true)
    vi.mocked(checkBluetoothPrinterReachability).mockReturnValue('unreachable')
    const btEvent = {
      ...event,
      bluetooth_printing_enabled: true,
    } as unknown as EdgeBundleEvent
    const showToast = vi.fn()
    const promise = offerPaymentReceipt({
      paymentId: 57,
      event: btEvent,
      showToast,
      preferredTargetUuid: 'reg-1',
    })
    confirmReceiptPrintYes()
    await promise
    expect(printPaymentReceipt).not.toHaveBeenCalled()
    expect(showToast).toHaveBeenCalledWith('Bluetooth-Drucker nicht erreichbar.', 'err')
    expect(api).toHaveBeenCalledWith('/v1/payments/57/receipt/print', {
      method: 'POST',
      body: JSON.stringify({ station_uuid: 'reg-1' }),
    })
  })

  it('falls back to stations when Bluetooth print fails after probe', async () => {
    vi.mocked(isAndroidApp).mockReturnValue(true)
    vi.mocked(isBluetoothPrinterConfigured).mockReturnValue(true)
    vi.mocked(checkBluetoothPrinterReachability).mockReturnValue('reachable')
    vi.mocked(printPaymentReceipt).mockRejectedValue(new Error('BT write failed'))
    const btEvent = {
      ...event,
      bluetooth_printing_enabled: true,
    } as unknown as EdgeBundleEvent
    const showToast = vi.fn()
    const promise = offerPaymentReceipt({
      paymentId: 58,
      event: btEvent,
      showToast,
      preferredTargetUuid: 'reg-1',
    })
    confirmReceiptPrintYes()
    await expect(promise).resolves.toBeUndefined()
    expect(showToast).toHaveBeenCalledWith('BT write failed', 'err')
    expect(api).toHaveBeenCalledWith('/v1/payments/58/receipt/print', {
      method: 'POST',
      body: JSON.stringify({ station_uuid: 'reg-1' }),
    })
  })

  it('tries Bluetooth then stations on older APK without probe', async () => {
    vi.mocked(isAndroidApp).mockReturnValue(true)
    vi.mocked(isBluetoothPrinterConfigured).mockReturnValue(true)
    vi.mocked(checkBluetoothPrinterReachability).mockReturnValue('unknown')
    vi.mocked(printPaymentReceipt).mockRejectedValue(new Error('offline'))
    const btEvent = {
      ...event,
      bluetooth_printing_enabled: true,
    } as unknown as EdgeBundleEvent
    const showToast = vi.fn()
    const promise = offerPaymentReceipt({
      paymentId: 59,
      event: btEvent,
      showToast,
      preferredTargetUuid: 'reg-1',
    })
    confirmReceiptPrintYes()
    await expect(promise).resolves.toBeUndefined()
    expect(printPaymentReceipt).toHaveBeenCalled()
    expect(api).toHaveBeenCalledWith('/v1/payments/59/receipt/print', {
      method: 'POST',
      body: JSON.stringify({ station_uuid: 'reg-1' }),
    })
  })

  it('skips Bluetooth when event flag is off even if a printer is paired', async () => {
    vi.mocked(isAndroidApp).mockReturnValue(true)
    vi.mocked(isBluetoothPrinterConfigured).mockReturnValue(true)
    const noBtEvent = {
      ...event,
      bluetooth_printing_enabled: false,
    } as unknown as EdgeBundleEvent
    const showToast = vi.fn()
    const promise = offerPaymentReceipt({
      paymentId: 56,
      event: noBtEvent,
      showToast,
      preferredTargetUuid: 'reg-1',
    })
    confirmReceiptPrintYes()
    await promise
    expect(printPaymentReceipt).not.toHaveBeenCalled()
    expect(api).toHaveBeenCalledWith('/v1/payments/56/receipt/print', {
      method: 'POST',
      body: JSON.stringify({ station_uuid: 'reg-1' }),
    })
  })

  it('offerPaymentReceiptAfterSettle resolves even when Bluetooth and stations fail', async () => {
    vi.mocked(isAndroidApp).mockReturnValue(true)
    vi.mocked(isBluetoothPrinterConfigured).mockReturnValue(true)
    vi.mocked(checkBluetoothPrinterReachability).mockReturnValue('reachable')
    vi.mocked(printPaymentReceipt).mockRejectedValue(new Error('BT down'))
    vi.mocked(api).mockRejectedValue(new Error('station down'))
    const btEvent = {
      ...event,
      bluetooth_printing_enabled: true,
    } as unknown as EdgeBundleEvent
    const showToast = vi.fn()
    const promise = offerPaymentReceiptAfterSettle({
      paymentId: 60,
      event: btEvent,
      showToast,
      preferredTargetUuid: 'reg-1',
    })
    confirmReceiptPrintYes()
    await expect(promise).resolves.toBeUndefined()
  })
})
