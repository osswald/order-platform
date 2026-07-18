import { ref } from 'vue'
import type { EdgeBundleEvent } from '@/types/api'
import { api, isAndroidApp } from '@/api'
import {
  isBluetoothPrinterConfigured,
  printPaymentReceipt,
} from './androidPrinter'
import { receiptPrintTargets } from './bundleHelpers'
import type { ToastState } from '@/types/cart'

export const receiptPromptOpen = ref(false)
export const receiptPromptStep = ref<'ask' | 'station'>('ask')
export const receiptPromptTargets = ref<Array<{ uuid: string; label: string }>>([])
export const receiptPromptBusy = ref(false)

let resolveAsk: ((value: boolean) => void) | null = null
let rejectAsk: ((reason?: unknown) => void) | null = null
let resolveStation: ((value: string) => void) | null = null
let rejectStation: ((reason?: unknown) => void) | null = null

function askPrintReceipt(): Promise<boolean> {
  receiptPromptStep.value = 'ask'
  receiptPromptTargets.value = []
  receiptPromptOpen.value = true
  return new Promise((resolve, reject) => {
    resolveAsk = resolve
    rejectAsk = reject
  })
}

/** Shared network-printer picker (payment receipts, voucher slips, …). */
export function pickReceiptStation(
  targets: Array<{ uuid: string; label: string }>,
): Promise<string> {
  receiptPromptTargets.value = targets
  receiptPromptStep.value = 'station'
  receiptPromptOpen.value = true
  return new Promise((resolve, reject) => {
    resolveStation = resolve
    rejectStation = reject
  })
}

export async function printPaymentReceiptToStation(
  paymentId: number | string,
  stationUuid: string,
): Promise<unknown> {
  return api(`/v1/payments/${encodeURIComponent(String(paymentId))}/receipt/print`, {
    method: 'POST',
    body: JSON.stringify({ station_uuid: stationUuid }),
  })
}

type ShowToastFn = (message: string, type?: ToastState['type']) => void

async function printToStation(
  paymentId: number | string,
  stationUuid: string,
  showToast?: ShowToastFn,
): Promise<void> {
  receiptPromptBusy.value = true
  try {
    await printPaymentReceiptToStation(paymentId, stationUuid)
    showToast?.('Beleg an Drucker gesendet.', 'ok')
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : 'Drucken fehlgeschlagen.'
    showToast?.(message, 'err')
    throw e
  } finally {
    receiptPromptBusy.value = false
  }
}

async function printBluetooth(
  paymentId: number | string,
  showToast?: ShowToastFn,
  { reprint = false }: { reprint?: boolean } = {},
): Promise<void> {
  receiptPromptBusy.value = true
  try {
    await printPaymentReceipt(paymentId, { reprint })
    showToast?.('Beleg gedruckt.', 'ok')
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : 'Drucken fehlgeschlagen.'
    showToast?.(message, 'err')
    throw e
  } finally {
    receiptPromptBusy.value = false
  }
}

export function offerPaymentReceiptEnabled(event: EdgeBundleEvent | null | undefined): boolean {
  return Boolean(event?.offer_payment_receipt)
}

export interface OfferPaymentReceiptOptions {
  paymentId: number | string
  event: EdgeBundleEvent
  showToast?: ShowToastFn
  reprint?: boolean
  preferredTargetUuid?: string | null
}

export async function offerPaymentReceipt({
  paymentId,
  event,
  showToast,
  reprint = false,
  preferredTargetUuid = null,
}: OfferPaymentReceiptOptions): Promise<void> {
  if (paymentId == null || paymentId === '') return
  if (!reprint && !offerPaymentReceiptEnabled(event)) return

  let wantPrint = false
  try {
    wantPrint = await askPrintReceipt()
  } catch {
    return
  }
  if (!wantPrint) return

  const btReady = isAndroidApp() && isBluetoothPrinterConfigured()
  if (btReady) {
    await printBluetooth(paymentId, showToast, { reprint })
    return
  }

  const targets = receiptPrintTargets(event)
  if (!targets.length) {
    showToast?.('Kein Drucker konfiguriert.', 'err')
    return
  }

  const preferred = String(preferredTargetUuid || '').trim()
  if (preferred && targets.some((t) => t.uuid === preferred)) {
    await printToStation(paymentId, preferred, showToast)
    return
  }

  if (targets.length === 1) {
    await printToStation(paymentId, targets[0].uuid, showToast)
    return
  }

  let stationUuid: string | null = null
  try {
    stationUuid = await pickReceiptStation(targets)
  } catch {
    return
  }
  if (!stationUuid) return
  await printToStation(paymentId, stationUuid, showToast)
}

export function confirmReceiptPrintYes(): void {
  receiptPromptOpen.value = false
  const r = resolveAsk
  resolveAsk = null
  rejectAsk = null
  if (r) r(true)
}

export function confirmReceiptPrintNo(): void {
  receiptPromptOpen.value = false
  const r = resolveAsk
  resolveAsk = null
  rejectAsk = null
  if (r) r(false)
}

export function cancelReceiptPrompt(): void {
  receiptPromptOpen.value = false
  if (receiptPromptStep.value === 'ask') {
    const rej = rejectAsk
    resolveAsk = null
    rejectAsk = null
    if (rej) rej(new Error('cancelled'))
  } else {
    const rej = rejectStation
    resolveStation = null
    rejectStation = null
    if (rej) rej(new Error('cancelled'))
  }
}

export function selectReceiptStation(uuid: string): void {
  receiptPromptOpen.value = false
  const r = resolveStation
  resolveStation = null
  rejectStation = null
  if (r) r(uuid)
}
