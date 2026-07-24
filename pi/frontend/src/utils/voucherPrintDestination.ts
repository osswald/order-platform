import { isAndroidApp } from '@/api'
import type { EdgeBundleEvent, LocalOrderCreate, LocalOrderCreatedResponse } from '@/types/api'
import type { ToastState } from '@/types/cart'
import {
  isBluetoothPrinterConfigured,
  printEscposBase64,
} from './androidPrinter'
import { receiptPrintTargets } from './bundleHelpers'
import { bluetoothPrintingEnabled, pickReceiptStation } from './paymentReceiptPrompt'

type ShowToastFn = (message: string, type?: ToastState['type']) => void

export type VoucherPrintPlan =
  | { mode: 'bluetooth' }
  | { mode: 'network'; stationUuid: string }
  | { mode: 'none' }

/**
 * Decide how waiter voucher slips should be delivered before order submit.
 * Bluetooth (if event-enabled and configured) wins; otherwise pick a network printer; if none, warn and continue.
 */
export async function resolveWaiterVoucherPrintPlan(
  event: EdgeBundleEvent | null | undefined,
  {
    hasVoucherSales,
    showToast,
  }: {
    hasVoucherSales: boolean
    showToast?: ShowToastFn
  },
): Promise<VoucherPrintPlan> {
  if (!hasVoucherSales) return { mode: 'none' }

  if (
    isAndroidApp() &&
    isBluetoothPrinterConfigured() &&
    bluetoothPrintingEnabled(event)
  ) {
    return { mode: 'bluetooth' }
  }

  const targets = receiptPrintTargets(event)
  if (!targets.length) {
    showToast?.(
      'Kein Drucker für Gutscheine verfügbar. Bestellung wird ohne Gutscheindruck gespeichert.',
      'err',
    )
    return { mode: 'none' }
  }

  if (targets.length === 1) {
    return { mode: 'network', stationUuid: targets[0].uuid }
  }

  const stationUuid = await pickReceiptStation(targets)
  return { mode: 'network', stationUuid }
}

/** Apply create-body fields for the chosen waiter voucher print plan. */
export function applyVoucherPrintPlanToOrderBody(
  body: LocalOrderCreate,
  plan: VoucherPrintPlan,
): void {
  if (plan.mode === 'bluetooth') {
    body.voucher_print_via_bluetooth = true
    body.voucher_printer_station_uuid = null
    return
  }
  if (plan.mode === 'network') {
    body.voucher_print_via_bluetooth = false
    body.voucher_printer_station_uuid = plan.stationUuid
    return
  }
  body.voucher_print_via_bluetooth = false
  body.voucher_printer_station_uuid = null
}

/** After create: send Bluetooth ESC/POS payloads when the plan requested them. */
export function deliverWaiterVoucherPrints(
  res: LocalOrderCreatedResponse,
  plan: VoucherPrintPlan,
  showToast?: ShowToastFn,
): void {
  if (plan.mode !== 'bluetooth') return
  const payloads = res.voucher_escpos_payloads || []
  if (!payloads.length) {
    showToast?.('Gutscheine konnten lokal nicht gedruckt werden (keine Daten).', 'err')
    return
  }
  let failed = 0
  for (const payload of payloads) {
    const result = printEscposBase64(payload)
    if (!result.ok) failed += 1
  }
  if (failed) {
    showToast?.(
      failed === payloads.length
        ? 'Gutscheindruck fehlgeschlagen.'
        : `${failed} von ${payloads.length} Gutscheinen nicht gedruckt.`,
      'err',
    )
  }
}
