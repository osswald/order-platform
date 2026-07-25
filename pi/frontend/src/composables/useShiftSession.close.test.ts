import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import type { EdgeBundleEvent, ShiftSessionRead } from '@/types/api'

vi.mock('@/api', () => ({
  api: vi.fn(),
}))

vi.mock('@/utils/androidPrinter', () => ({
  printEscposBase64: vi.fn(() => ({ ok: true })),
}))

vi.mock('@/utils/paymentReceiptPrompt', () => ({
  resolveBluetoothPrintGate: vi.fn(() => 'skip'),
}))

vi.mock('@/utils/receiptCharset', () => ({
  getReceiptCharset: vi.fn(() => 'cp437'),
}))

vi.mock('@/utils/receiptPaperWidth', () => ({
  getReceiptPaperWidth: vi.fn(() => 58),
}))

import { api } from '@/api'
import {
  cancelShiftClose,
  confirmShiftClose,
  maybeEndShiftOnSwitch,
  shiftCloseAmountChf,
  shiftCloseDialogOpen,
  shiftCloseError,
} from './useShiftSession'
import ShiftCloseDialog from '@/components/ShiftCloseDialog.vue'

function shiftEvent(): EdgeBundleEvent {
  return {
    id: 1,
    name: 'Fest',
    shift_settlement_enabled: true,
  } as EdgeBundleEvent
}

function activeShift(overrides: Partial<ShiftSessionRead> = {}): ShiftSessionRead {
  return {
    id: 42,
    wallet_cents: 1250,
    ...overrides,
  } as ShiftSessionRead
}

describe('shift close cash count (no window.prompt)', () => {
  beforeEach(() => {
    vi.mocked(api).mockReset()
    shiftCloseDialogOpen.value = false
    shiftCloseAmountChf.value = ''
    shiftCloseError.value = ''
    window.confirm = vi.fn(() => true) as unknown as typeof window.confirm
    window.alert = vi.fn() as unknown as typeof window.alert
    window.prompt = vi.fn(() => 'should-not-be-used') as unknown as typeof window.prompt
  })

  it('opens in-app dialog instead of window.prompt and closes shift on confirm', async () => {
    vi.mocked(api).mockImplementation(async (path: string, init?: RequestInit) => {
      if (String(path).includes('/shift-session/active')) return activeShift()
      if (String(path).includes('/close') && init?.method === 'POST') return { ok: true }
      if (String(path).includes('/print')) return { ok: true }
      throw new Error(`unexpected ${path}`)
    })

    const promise = maybeEndShiftOnSwitch({
      eventId: 1,
      subjectType: 'waiter',
      waiterUuid: 'w1',
      event: shiftEvent(),
    })
    await flushPromises()
    expect(window.prompt).not.toHaveBeenCalled()
    expect(shiftCloseDialogOpen.value).toBe(true)
    expect(shiftCloseAmountChf.value).toBe('12.50')

    const wrapper = mount(ShiftCloseDialog, { attachTo: document.body })
    await nextTick()
    expect(wrapper.text()).toContain('Kassenbestand zählen')
    await wrapper.find('input.amount-input').setValue('12.50')
    await wrapper.findAll('button').find((b) => b.text() === 'Beenden')!.trigger('click')
    await flushPromises()

    const ok = await promise
    expect(ok).toBe(true)
    expect(shiftCloseDialogOpen.value).toBe(false)
    expect(api).toHaveBeenCalledWith(
      '/v1/shift-session/42/close',
      expect.objectContaining({ method: 'POST' }),
    )
    wrapper.unmount()
  })

  it('cancel does not close the shift', async () => {
    vi.mocked(api).mockImplementation(async (path: string) => {
      if (String(path).includes('/shift-session/active')) return activeShift()
      throw new Error(`unexpected ${path}`)
    })

    const promise = maybeEndShiftOnSwitch({
      eventId: 1,
      subjectType: 'waiter',
      waiterUuid: 'w1',
      event: shiftEvent(),
    })
    await flushPromises()
    cancelShiftClose()
    const ok = await promise
    expect(ok).toBe(false)
    expect(vi.mocked(api).mock.calls.some((c) => String(c[0]).includes('/close'))).toBe(false)
  })

  it('keeps dialog open on invalid amount', async () => {
    vi.mocked(api).mockImplementation(async (path: string) => {
      if (String(path).includes('/shift-session/active')) return activeShift()
      throw new Error(`unexpected ${path}`)
    })
    const promise = maybeEndShiftOnSwitch({
      eventId: 1,
      subjectType: 'waiter',
      waiterUuid: 'w1',
      event: shiftEvent(),
    })
    await flushPromises()
    shiftCloseAmountChf.value = 'abc'
    await confirmShiftClose()
    expect(shiftCloseDialogOpen.value).toBe(true)
    expect(shiftCloseError.value).toContain('Ungültig')
    cancelShiftClose()
    await promise
  })
})
