import { describe, expect, it, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import LinePositionSheet from './LinePositionSheet.vue'
import { defaultBundle } from '../../tests/fixtures/bundle'

const line = {
  lineId: 'l1',
  article_id: 10,
  qty: 1,
  note: '',
  additions: [],
}

describe('LinePositionSheet', () => {
  let wrapper

  afterEach(() => {
    wrapper?.unmount()
    document.body.innerHTML = ''
  })

  it('emits save with note from comment section', async () => {
    wrapper = mount(LinePositionSheet, {
      props: {
        open: true,
        line,
        articles: { 10: { id: 10, name: 'Bier', price: 5 } },
        event: defaultBundle().events[0],
        positionCommentsEnabled: true,
        discountsEnabled: false,
        presets: [{ id: 1, text: 'ohne Zwiebeln' }],
      },
      attachTo: document.body,
    })
    const chip = document.body.querySelector('.chip-btn')
    expect(chip).toBeTruthy()
    await chip.click()
    await document.body.querySelector('.btn.primary').click()
    expect(wrapper.emitted('save')?.[0]?.[0]).toEqual({
      lineId: 'l1',
      note: 'ohne Zwiebeln',
    })
  })

  it('shows both section tabs when comment and discount are enabled', () => {
    wrapper = mount(LinePositionSheet, {
      props: {
        open: true,
        line,
        articles: { 10: { id: 10, name: 'Bier', price: 5 } },
        event: { ...defaultBundle().events[0], discounts_enabled: true },
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
