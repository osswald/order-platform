import { ref } from 'vue'
import { api, isAndroidApp } from '../api'
import {
  isBluetoothPrinterConfigured,
  printPaymentReceipt,
} from './androidPrinter'
import { receiptPrintTargets } from './bundleHelpers'

export const receiptPromptOpen = ref(false)
export const receiptPromptStep = ref('ask')
export const receiptPromptTargets = ref([])
export const receiptPromptBusy = ref(false)

let resolveAsk = null
let rejectAsk = null
let resolveStation = null
let rejectStation = null

function askPrintReceipt() {
  receiptPromptStep.value = 'ask'
  receiptPromptTargets.value = []
  receiptPromptOpen.value = true
  return new Promise((resolve, reject) => {
    resolveAsk = resolve
    rejectAsk = reject
  })
}

function pickReceiptStation(targets) {
  receiptPromptTargets.value = targets
  receiptPromptStep.value = 'station'
  receiptPromptOpen.value = true
  return new Promise((resolve, reject) => {
    resolveStation = resolve
    rejectStation = reject
  })
}

export async function printPaymentReceiptToStation(paymentId, stationUuid) {
  return api(`/v1/payments/${encodeURIComponent(paymentId)}/receipt/print`, {
    method: 'POST',
    body: JSON.stringify({ station_uuid: stationUuid }),
  })
}

async function printToStation(paymentId, stationUuid, showToast) {
  receiptPromptBusy.value = true
  try {
    await printPaymentReceiptToStation(paymentId, stationUuid)
    showToast?.('Beleg an Drucker gesendet.', 'ok')
  } catch (e) {
    showToast?.(e.message || 'Drucken fehlgeschlagen.', 'err')
    throw e
  } finally {
    receiptPromptBusy.value = false
  }
}

async function printBluetooth(paymentId, showToast, { reprint = false } = {}) {
  receiptPromptBusy.value = true
  try {
    await printPaymentReceipt(paymentId, { reprint })
    showToast?.('Beleg gedruckt.', 'ok')
  } catch (e) {
    showToast?.(e.message || 'Drucken fehlgeschlagen.', 'err')
    throw e
  } finally {
    receiptPromptBusy.value = false
  }
}

/**
 * Ask whether to print a payment receipt; route to Bluetooth or station printer.
 * @param {{ paymentId: number|string, event: object, showToast?: Function, reprint?: boolean }} opts
 */
export async function offerPaymentReceipt({ paymentId, event, showToast, reprint = false }) {
  if (paymentId == null || paymentId === '') return

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

  if (targets.length === 1) {
    await printToStation(paymentId, targets[0].uuid, showToast)
    return
  }

  let stationUuid = null
  try {
    stationUuid = await pickReceiptStation(targets)
  } catch {
    return
  }
  if (!stationUuid) return
  await printToStation(paymentId, stationUuid, showToast)
}

export function confirmReceiptPrintYes() {
  receiptPromptOpen.value = false
  const r = resolveAsk
  resolveAsk = null
  rejectAsk = null
  if (r) r(true)
}

export function confirmReceiptPrintNo() {
  receiptPromptOpen.value = false
  const r = resolveAsk
  resolveAsk = null
  rejectAsk = null
  if (r) r(false)
}

export function cancelReceiptPrompt() {
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

export function selectReceiptStation(uuid) {
  receiptPromptOpen.value = false
  const r = resolveStation
  resolveStation = null
  rejectStation = null
  if (r) r(uuid)
}
