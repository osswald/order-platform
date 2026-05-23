import { api } from '../api'

function bridge() {
  if (typeof window === 'undefined') return null
  return window.AndroidPrinter || null
}

function parseResult(raw) {
  if (typeof raw === 'boolean') return { ok: raw }
  if (!raw) return { ok: false, error: 'Keine Antwort vom Android-Drucker.' }
  if (typeof raw === 'object') return raw
  try {
    return JSON.parse(raw)
  } catch {
    return { ok: false, error: String(raw) }
  }
}

function call(method, ...args) {
  const b = bridge()
  if (!b || typeof b[method] !== 'function') {
    return { ok: false, error: 'Android-Drucker ist nicht verfügbar.' }
  }
  try {
    return parseResult(b[method](...args))
  } catch (e) {
    return { ok: false, error: e?.message || 'Android-Druckerfehler.' }
  }
}

export function isAndroidPrinterAvailable() {
  return Boolean(bridge())
}

export function permissionStatus() {
  return call('permissionStatus')
}

export function requestPrinterPermissions() {
  return call('requestPermissions')
}

export function listPairedPrinters() {
  const result = call('listPairedPrinters')
  if (!result.ok) return result
  return { ...result, printers: Array.isArray(result.printers) ? result.printers : [] }
}

export function getSelectedPrinter() {
  return call('getSelectedPrinter')
}

export function setSelectedPrinter(address) {
  return call('setSelectedPrinter', address)
}

export function printEscposBase64(payload) {
  return call('printEscposBase64', payload)
}

export async function printPaymentReceipt(paymentId, { reprint = false } = {}) {
  const data = await api(`/v1/payments/${encodeURIComponent(paymentId)}/receipt`, {
    method: 'POST',
    body: JSON.stringify({ reprint }),
  })
  const result = printEscposBase64(data.escpos_payload)
  if (!result.ok) {
    throw new Error(result.error || 'Beleg konnte nicht gedruckt werden.')
  }
  return result
}

export async function printTestReceipt(eventId) {
  const data = await api('/v1/printers/test-receipt', {
    method: 'POST',
    body: JSON.stringify({ event_id: eventId || null }),
  })
  const result = printEscposBase64(data.escpos_payload)
  if (!result.ok) {
    throw new Error(result.error || 'Testbeleg konnte nicht gedruckt werden.')
  }
  return result
}
