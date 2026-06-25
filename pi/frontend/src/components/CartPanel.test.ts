import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import CartPanel from './CartPanel.vue'
import { defaultBundle } from '@tests/fixtures/bundle'
import type { EdgeBundleEvent } from '@/types/api'

const sampleLine = {
  lineId: 'l1',
  article_id: 10,
  qty: 1,
  note: 'warm',
  additions: [],
}

const testEvent = defaultBundle().events![0] as EdgeBundleEvent

describe('CartPanel position comments', () => {
  it('shows comment button when position comments are enabled', () => {
    const wrapper = mount(CartPanel, {
      props: {
        lines: [sampleLine],
        articles: { 10: { id: 10, name: 'Bier', price: 5 } },
        event: testEvent,
        positionCommentsEnabled: true,
      },
    })
    expect(wrapper.find('.cart-comment-btn').exists()).toBe(true)
    expect(wrapper.text()).toContain('warm')
  })

  it('hides comment button when position comments are disabled', () => {
    const wrapper = mount(CartPanel, {
      props: {
        lines: [sampleLine],
        articles: { 10: { id: 10, name: 'Bier', price: 5 } },
        event: testEvent,
        positionCommentsEnabled: false,
      },
    })
    expect(wrapper.find('.cart-comment-btn').exists()).toBe(false)
  })

  it('emits tap-comment when comment button is clicked', async () => {
    const wrapper = mount(CartPanel, {
      props: {
        lines: [sampleLine],
        articles: { 10: { id: 10, name: 'Bier', price: 5 } },
        event: testEvent,
        positionCommentsEnabled: true,
      },
    })
    await wrapper.find('.cart-comment-btn').trigger('click')
    expect(wrapper.emitted('tap-comment')?.[0]?.[0]).toEqual(sampleLine)
  })
})
