/** Per-device payment receipt charset (Bluetooth ESC/POS). */

export const RECEIPT_CHARSET_STORAGE_KEY = 'pi_receipt_charset'

export const CHARSET_PC858 = 'pc858'
export const CHARSET_PC850 = 'pc850'
export const CHARSET_CP1252 = 'cp1252'
export const CHARSET_ASCII = 'ascii'

export const RECEIPT_CHARSET_OPTIONS = [
  { value: CHARSET_PC858, label: 'Standard (PC858)' },
  { value: CHARSET_PC850, label: 'PC850 (viele Bluetooth-Drucker)' },
  { value: CHARSET_CP1252, label: 'Windows-1252 (PC1252)' },
  { value: CHARSET_ASCII, label: 'ASCII (ae/oe/ue)' },
] as const

export type ReceiptCharset = (typeof RECEIPT_CHARSET_OPTIONS)[number]['value']

const VALID = new Set<string>(RECEIPT_CHARSET_OPTIONS.map((opt) => opt.value))

export function getReceiptCharset(): ReceiptCharset {
  if (typeof localStorage === 'undefined') return CHARSET_PC858
  const stored = localStorage.getItem(RECEIPT_CHARSET_STORAGE_KEY)
  return stored && VALID.has(stored) ? (stored as ReceiptCharset) : CHARSET_PC858
}

export function setReceiptCharset(value: string): void {
  if (typeof localStorage === 'undefined') return
  const next = VALID.has(value) ? value : CHARSET_PC858
  localStorage.setItem(RECEIPT_CHARSET_STORAGE_KEY, next)
}
