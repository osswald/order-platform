import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  CHARSET_PC850,
  CHARSET_PC858,
  getReceiptCharset,
  setReceiptCharset,
} from './receiptCharset'

describe('receiptCharset', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', {
      store: {} as Record<string, string>,
      getItem(key: string) {
        return this.store[key] ?? null
      },
      setItem(key: string, value: string) {
        this.store[key] = value
      },
      removeItem(key: string) {
        delete this.store[key]
      },
      clear() {
        this.store = {}
      },
    })
  })

  it('defaults to pc858', () => {
    expect(getReceiptCharset()).toBe(CHARSET_PC858)
  })

  it('persists valid charset', () => {
    setReceiptCharset(CHARSET_PC850)
    expect(getReceiptCharset()).toBe(CHARSET_PC850)
  })

  it('falls back to pc858 for invalid values', () => {
    setReceiptCharset('invalid')
    expect(getReceiptCharset()).toBe(CHARSET_PC858)
  })
})
