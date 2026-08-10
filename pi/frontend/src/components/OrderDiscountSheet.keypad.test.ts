import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import OrderDiscountSheet from './OrderDiscountSheet.vue'

describe('OrderDiscountSheet custom percent keypad', () => {
  it('uses on-screen percent keypad for Andere', async () => {
    const wrapper = mount(OrderDiscountSheet, {
      props: {
        open: true,
        lines: [],
        articles: {},
        currency: 'CHF',
      },
      attachTo: document.body,
      global: { stubs: { teleport: true } },
    })
    const andere = wrapper.findAll('button.chip-btn').find((b) => b.text() === 'Andere')
    expect(andere).toBeTruthy()
    await andere!.trigger('click')
    expect(wrapper.find('input[type="number"]').exists()).toBe(false)
    expect(wrapper.find('.percent-keypad').exists()).toBe(true)
    const keys = wrapper.findAll('.percent-keypad button.key')
    await keys.find((b) => b.text() === '7')!.trigger('click')
    expect(wrapper.find('.percent-keypad .display').text()).toContain('7%')
    wrapper.unmount()
  })
})
