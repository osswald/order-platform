import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  checkBluetoothPrinterReachability,
  checkSelectedPrinter,
  hasBluetoothPrinterProbe,
  isBluetoothPrinterConfigured,
  isBluetoothPrinterReachable,
} from './androidPrinter'

describe('androidPrinter reachability', () => {
  afterEach(() => {
    delete window.AndroidPrinter
  })

  it('reports probe missing on older APK', () => {
    window.AndroidPrinter = {
      getSelectedPrinter: () => JSON.stringify({ ok: true, address: 'AA:BB' }),
    }
    expect(hasBluetoothPrinterProbe()).toBe(false)
    expect(checkBluetoothPrinterReachability()).toBe('unknown')
    expect(isBluetoothPrinterReachable()).toBe(false)
  })

  it('checkSelectedPrinter returns bridge result', () => {
    window.AndroidPrinter = {
      checkSelectedPrinter: () => JSON.stringify({ ok: true, address: 'AA:BB:CC:DD:EE:FF' }),
    }
    expect(checkSelectedPrinter()).toEqual({ ok: true, address: 'AA:BB:CC:DD:EE:FF' })
  })

  it('treats successful probe as reachable when a printer is selected', () => {
    window.AndroidPrinter = {
      getSelectedPrinter: () => JSON.stringify({ ok: true, address: 'AA:BB:CC:DD:EE:FF' }),
      checkSelectedPrinter: () => JSON.stringify({ ok: true, address: 'AA:BB:CC:DD:EE:FF' }),
    }
    expect(isBluetoothPrinterConfigured()).toBe(true)
    expect(hasBluetoothPrinterProbe()).toBe(true)
    expect(checkBluetoothPrinterReachability()).toBe('reachable')
    expect(isBluetoothPrinterReachable()).toBe(true)
  })

  it('treats failed probe as unreachable', () => {
    window.AndroidPrinter = {
      getSelectedPrinter: () => JSON.stringify({ ok: true, address: 'AA:BB:CC:DD:EE:FF' }),
      checkSelectedPrinter: () => JSON.stringify({ ok: false, error: 'read failed' }),
    }
    expect(checkBluetoothPrinterReachability()).toBe('unreachable')
    expect(isBluetoothPrinterReachable()).toBe(false)
  })

  it('is unreachable when no printer is selected', () => {
    window.AndroidPrinter = {
      getSelectedPrinter: () => JSON.stringify({ ok: true, address: '' }),
      checkSelectedPrinter: vi.fn(() => JSON.stringify({ ok: true })),
    }
    expect(isBluetoothPrinterConfigured()).toBe(false)
    expect(checkBluetoothPrinterReachability()).toBe('unreachable')
    expect(window.AndroidPrinter.checkSelectedPrinter).not.toHaveBeenCalled()
  })
})
