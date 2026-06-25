import { api } from '@/api'
import type { PaymentReceiptEscposResponse } from '@/types/api'
import { getReceiptPaperWidth } from './receiptPaperWidth'

interface BridgeResult extends AndroidBridgeResult {
  printers?: unknown[]
  address?: string
}

function bridge(): Record<string, (...args: unknown[]) => unknown> | null {
  if (typeof window === 'undefined') return null
  return window.AndroidPrinter || null
}

function parseResult(raw: unknown): BridgeResult {
  if (typeof raw === 'boolean') return { ok: raw }
  if (!raw) return { ok: false, error: 'Keine Antwort vom Android-Drucker.' }
  if (typeof raw === 'object') return raw as BridgeResult
  try {
    return JSON.parse(String(raw)) as BridgeResult
  } catch {
    return { ok: false, error: String(raw) }
  }
}

function call(method: string, ...args: unknown[]): BridgeResult {
  const b = bridge()
  if (!b || typeof b[method] !== 'function') {
    return { ok: false, error: 'Android-Drucker ist nicht verfügbar.' }
  }
  try {
    return parseResult(b[method](...args))
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : 'Android-Druckerfehler.'
    return { ok: false, error: message }
  }
}

export function isAndroidPrinterAvailable(): boolean {
  return Boolean(bridge())
}

/** Android app with a paired Bluetooth printer selected. */
export function isBluetoothPrinterConfigured(): boolean {
  if (!isAndroidPrinterAvailable()) return false
  const sel = getSelectedPrinter()
  if (sel?.ok === false) return false
  return Boolean(String(sel?.address || '').trim())
}

export function permissionStatus(): BridgeResult {
  return call('permissionStatus')
}

export function requestPrinterPermissions(): BridgeResult {
  return call('requestPermissions')
}

export function listPairedPrinters(): BridgeResult & { printers: unknown[] } {
  const result = call('listPairedPrinters')
  if (!result.ok) return { ...result, printers: [] }
  return { ...result, printers: Array.isArray(result.printers) ? result.printers : [] }
}

export function getSelectedPrinter(): BridgeResult {
  return call('getSelectedPrinter')
}

export function setSelectedPrinter(address: string): BridgeResult {
  return call('setSelectedPrinter', address)
}

export function printEscposBase64(payload: string): BridgeResult {
  return call('printEscposBase64', payload)
}

export async function printPaymentReceipt(
  paymentId: number | string,
  { reprint = false }: { reprint?: boolean } = {},
): Promise<BridgeResult> {
  const data = await api<PaymentReceiptEscposResponse>(
    `/v1/payments/${encodeURIComponent(String(paymentId))}/receipt`,
    {
      method: 'POST',
      body: JSON.stringify({ reprint, paper_width: getReceiptPaperWidth() }),
    },
  )
  const result = printEscposBase64(data.escpos_payload)
  if (!result.ok) {
    throw new Error(result.error || 'Beleg konnte nicht gedruckt werden.')
  }
  return result
}

export async function printTestReceipt(eventId: number | null): Promise<BridgeResult> {
  const data = await api<PaymentReceiptEscposResponse>('/v1/printers/test-receipt', {
    method: 'POST',
    body: JSON.stringify({ event_id: eventId || null, paper_width: getReceiptPaperWidth() }),
  })
  const result = printEscposBase64(data.escpos_payload)
  if (!result.ok) {
    throw new Error(result.error || 'Testbeleg konnte nicht gedruckt werden.')
  }
  return result
}
