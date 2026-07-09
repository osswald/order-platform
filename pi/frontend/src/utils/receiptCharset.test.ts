import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  CHARSET_ASCII,
  CHARSET_PC850,
  CHARSET_PC858,
  getReceiptCharset,
  setReceiptCharset,
} from './receiptCharset'

describe('receiptCharset', () => {
  beforeEach(() => {
    const store: Record<string, string> = {}
    vi.stubGlobal('localStorage', {
      getItem(key: string) {
        return store[key] ?? null
      },
      setItem(key: string, value: string) {
        store[key] = value
      },
      removeItem(key: string) {
        delete store[key]
      },
      clear() {
        for (const key of Object.keys(store)) delete store[key]
      },
    })
  })

  it('defaults to pc858', () => {
    expect(getReceiptCharset()).toBe(CHARSET_PC858)
  })

  it('persists valid charset', () => {
    setReceiptCharset(CHARSET_PC850)
    expect(getReceiptCharset()).toBe(CHARSET_PC850)
    setReceiptCharset(CHARSET_ASCII)
    expect(getReceiptCharset()).toBe(CHARSET_ASCII)
  })

  it('falls back to pc858 for invalid values', () => {
    setReceiptCharset('invalid')
    expect(getReceiptCharset()).toBe(CHARSET_PC858)
  })
})
