/** Per-device payment receipt paper width (Bluetooth). */

export const RECEIPT_PAPER_WIDTH_STORAGE_KEY = 'pi_receipt_paper_width'

export const PAPER_WIDTH_80 = '80mm'
export const PAPER_WIDTH_58 = '58mm'
export const PAPER_WIDTH_53 = '53mm'

export const RECEIPT_PAPER_WIDTH_OPTIONS = [
  { value: PAPER_WIDTH_80, label: '80 mm (Standard)' },
  { value: PAPER_WIDTH_58, label: '58 mm' },
  { value: PAPER_WIDTH_53, label: '53 mm (schmal, Bluetooth)' },
]

const VALID = new Set([PAPER_WIDTH_80, PAPER_WIDTH_58, PAPER_WIDTH_53])

export function getReceiptPaperWidth() {
  if (typeof localStorage === 'undefined') return PAPER_WIDTH_80
  const stored = localStorage.getItem(RECEIPT_PAPER_WIDTH_STORAGE_KEY)
  return stored && VALID.has(stored) ? stored : PAPER_WIDTH_80
}

export function setReceiptPaperWidth(value: string): void {
  if (typeof localStorage === 'undefined') return
  const next = VALID.has(value) ? value : PAPER_WIDTH_80
  localStorage.setItem(RECEIPT_PAPER_WIDTH_STORAGE_KEY, next)
}
