import { describe, expect, it, afterEach, vi, beforeEach } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import LinePositionSheet from './LinePositionSheet.vue'
import { defaultBundle } from '@tests/fixtures/bundle'
import type { EdgeBundleEvent } from '@/types/api'

const isAndroidApp = vi.fn(() => false)

vi.mock('@/api/base', () => ({
  isAndroidApp: () => isAndroidApp(),
}))

const line = {
  lineId: 'l1',
  article_id: 10,
  qty: 1,
  note: '',
  additions: [],
}

const testEvent = defaultBundle().events![0] as EdgeBundleEvent

describe('LinePositionSheet', () => {
  let wrapper: VueWrapper | undefined

  beforeEach(() => {
    isAndroidApp.mockReturnValue(false)
  })

  afterEach(() => {
    wrapper?.unmount()
    document.body.innerHTML = ''
  })

  it('emits save with note from comment section presets', async () => {
    wrapper = mount(LinePositionSheet, {
      props: {
        open: true,
        line,
        articles: { 10: { id: 10, name: 'Bier', price: 5 } },
        event: testEvent,
        positionCommentsEnabled: true,
        discountsEnabled: false,
        presets: [{ id: 1, text: 'ohne Zwiebeln' }],
      },
      attachTo: document.body,
    })
    const chip = document.body.querySelector('.chip-btn') as HTMLElement | null
    expect(chip).toBeTruthy()
    await chip!.click()
    const primaryBtn = document.body.querySelector('.btn.primary') as HTMLElement | null
    expect(primaryBtn).toBeTruthy()
    await primaryBtn!.click()
    expect(wrapper.emitted('save')?.[0]?.[0]).toEqual({
      lineId: 'l1',
      note: 'ohne Zwiebeln',
    })
  })

  it('uses soft keyboard for comments on non-Android', async () => {
    wrapper = mount(LinePositionSheet, {
      props: {
        open: true,
        line,
        articles: { 10: { id: 10, name: 'Bier', price: 5 } },
        event: testEvent,
        positionCommentsEnabled: true,
        discountsEnabled: false,
        presets: [],
      },
      attachTo: document.body,
    })
    expect(document.body.querySelector('input.comment-input')).toBeNull()
    expect(document.body.querySelector('.soft-keyboard')).toBeTruthy()
  })

  it('uses native comment input on Android', async () => {
    isAndroidApp.mockReturnValue(true)
    wrapper = mount(LinePositionSheet, {
      props: {
        open: true,
        line,
        articles: { 10: { id: 10, name: 'Bier', price: 5 } },
        event: testEvent,
        positionCommentsEnabled: true,
        discountsEnabled: false,
        presets: [],
      },
      attachTo: document.body,
    })
    expect(document.body.querySelector('input.comment-input')).toBeTruthy()
    expect(document.body.querySelector('.soft-keyboard')).toBeNull()
  })

  it('shows both section tabs when comment and discount are enabled', () => {
    wrapper = mount(LinePositionSheet, {
      props: {
        open: true,
        line,
        articles: { 10: { id: 10, name: 'Bier', price: 5 } },
        event: { ...testEvent, discounts_enabled: true },
        positionCommentsEnabled: true,
        discountsEnabled: true,
        presets: [],
        initialTab: 'discount',
      },
      attachTo: document.body,
    })
    const tabLabels = [...document.body.querySelectorAll('.discount-tabs .tab-btn')].map(
      (el) => el.textContent?.trim(),
    )
    expect(tabLabels).toContain('Kommentar')
    expect(tabLabels).toContain('Rabatt')
  })
})
