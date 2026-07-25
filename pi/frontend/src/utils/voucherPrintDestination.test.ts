import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { EdgeBundleEvent, LocalOrderCreate, LocalOrderCreatedResponse } from '@/types/api'

vi.mock('./androidPrinter', () => ({
  printEscposBase64: vi.fn(() => ({ ok: true })),
}))

vi.mock('./bundleHelpers', () => ({
  receiptPrintTargets: vi.fn(() => []),
}))

vi.mock('./paymentReceiptPrompt', () => ({
  pickReceiptStation: vi.fn(),
  resolveBluetoothPrintGate: vi.fn(() => 'skip'),
  bluetoothPrinterConfiguredForEvent: vi.fn(() => false),
}))

import { printEscposBase64 } from './androidPrinter'
import { receiptPrintTargets } from './bundleHelpers'
import {
  bluetoothPrinterConfiguredForEvent,
  pickReceiptStation,
  resolveBluetoothPrintGate,
} from './paymentReceiptPrompt'
import {
  applyVoucherPrintPlanToOrderBody,
  deliverWaiterVoucherPrints,
  resolveWaiterVoucherPrintPlan,
} from './voucherPrintDestination'

describe('resolveWaiterVoucherPrintPlan', () => {
  beforeEach(() => {
    vi.mocked(resolveBluetoothPrintGate).mockReturnValue('skip')
    vi.mocked(bluetoothPrinterConfiguredForEvent).mockReturnValue(false)
    vi.mocked(receiptPrintTargets).mockReturnValue([])
    vi.mocked(pickReceiptStation).mockReset()
  })

  it('returns none when cart has no voucher sales', async () => {
    const plan = await resolveWaiterVoucherPrintPlan({} as EdgeBundleEvent, {
      hasVoucherSales: false,
    })
    expect(plan).toEqual({ mode: 'none' })
  })

  it('uses Bluetooth when gate is use (reachable)', async () => {
    vi.mocked(resolveBluetoothPrintGate).mockReturnValue('use')
    const plan = await resolveWaiterVoucherPrintPlan(
      { bluetooth_printing_enabled: true } as unknown as EdgeBundleEvent,
      { hasVoucherSales: true },
    )
    expect(plan).toEqual({ mode: 'bluetooth' })
    expect(pickReceiptStation).not.toHaveBeenCalled()
  })

  it('uses Bluetooth when gate is try (older APK)', async () => {
    vi.mocked(resolveBluetoothPrintGate).mockReturnValue('try')
    const plan = await resolveWaiterVoucherPrintPlan({} as EdgeBundleEvent, {
      hasVoucherSales: true,
    })
    expect(plan).toEqual({ mode: 'bluetooth' })
  })

  it('falls back to network when Bluetooth is configured but unreachable', async () => {
    vi.mocked(resolveBluetoothPrintGate).mockReturnValue('skip')
    vi.mocked(bluetoothPrinterConfiguredForEvent).mockReturnValue(true)
    vi.mocked(receiptPrintTargets).mockReturnValue([
      { uuid: 'st-1', label: 'Bar', kind: 'station' },
    ])
    const showToast = vi.fn()
    const plan = await resolveWaiterVoucherPrintPlan(
      { bluetooth_printing_enabled: true } as unknown as EdgeBundleEvent,
      { hasVoucherSales: true, showToast },
    )
    expect(plan).toEqual({ mode: 'network', stationUuid: 'st-1' })
    expect(showToast).toHaveBeenCalledWith('Bluetooth-Drucker nicht erreichbar.', 'err')
  })

  it('skips Bluetooth toast when gate skip and printer not configured for event', async () => {
    vi.mocked(resolveBluetoothPrintGate).mockReturnValue('skip')
    vi.mocked(bluetoothPrinterConfiguredForEvent).mockReturnValue(false)
    vi.mocked(receiptPrintTargets).mockReturnValue([
      { uuid: 'st-1', label: 'Bar', kind: 'station' },
    ])
    const showToast = vi.fn()
    const plan = await resolveWaiterVoucherPrintPlan(
      { bluetooth_printing_enabled: false } as unknown as EdgeBundleEvent,
      { hasVoucherSales: true, showToast },
    )
    expect(plan).toEqual({ mode: 'network', stationUuid: 'st-1' })
    expect(showToast).not.toHaveBeenCalledWith('Bluetooth-Drucker nicht erreichbar.', 'err')
  })

  it('auto-selects the only network printer when Bluetooth is absent', async () => {
    vi.mocked(receiptPrintTargets).mockReturnValue([
      { uuid: 'st-1', label: 'Bar', kind: 'station' },
    ])
    const plan = await resolveWaiterVoucherPrintPlan({} as EdgeBundleEvent, {
      hasVoucherSales: true,
    })
    expect(plan).toEqual({ mode: 'network', stationUuid: 'st-1' })
  })

  it('asks which network printer to use when several are available', async () => {
    vi.mocked(receiptPrintTargets).mockReturnValue([
      { uuid: 'st-1', label: 'Bar', kind: 'station' },
      { uuid: 'reg-1', label: 'Kasse: 1', kind: 'register' },
    ])
    vi.mocked(pickReceiptStation).mockResolvedValue('reg-1')
    const plan = await resolveWaiterVoucherPrintPlan({} as EdgeBundleEvent, {
      hasVoucherSales: true,
    })
    expect(pickReceiptStation).toHaveBeenCalled()
    expect(plan).toEqual({ mode: 'network', stationUuid: 'reg-1' })
  })

  it('warns and continues when no printers are available', async () => {
    const showToast = vi.fn()
    const plan = await resolveWaiterVoucherPrintPlan({} as EdgeBundleEvent, {
      hasVoucherSales: true,
      showToast,
    })
    expect(plan).toEqual({ mode: 'none' })
    expect(showToast).toHaveBeenCalledWith(expect.stringContaining('Kein Drucker'), 'err')
  })
})

describe('applyVoucherPrintPlanToOrderBody / deliverWaiterVoucherPrints', () => {
  it('sets bluetooth create flags', () => {
    const body = {} as LocalOrderCreate
    applyVoucherPrintPlanToOrderBody(body, { mode: 'bluetooth' })
    expect(body.voucher_print_via_bluetooth).toBe(true)
    expect(body.voucher_printer_station_uuid).toBeNull()
  })

  it('sets network station uuid', () => {
    const body = {} as LocalOrderCreate
    applyVoucherPrintPlanToOrderBody(body, { mode: 'network', stationUuid: 'st-9' })
    expect(body.voucher_print_via_bluetooth).toBe(false)
    expect(body.voucher_printer_station_uuid).toBe('st-9')
  })

  it('prints bluetooth payloads after create', () => {
    deliverWaiterVoucherPrints(
      { voucher_escpos_payloads: ['a', 'b'] } as LocalOrderCreatedResponse,
      { mode: 'bluetooth' },
    )
    expect(printEscposBase64).toHaveBeenCalledTimes(2)
  })
})
