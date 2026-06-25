import { describe, expect, it } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import PinKeypad from './PinKeypad.vue'

function keyButton(wrapper: VueWrapper, digit: string) {
  const btn = wrapper.findAll('button.key').find((b) => b.text() === digit)
  expect(btn).toBeTruthy()
  return btn!
}

describe('PinKeypad', () => {
  it('fills dots as digits are pressed', async () => {
    const wrapper = mount(PinKeypad, { props: { maxLength: 4 } })
    await keyButton(wrapper, '1').trigger('click')
    expect(wrapper.findAll('.dot.filled')).toHaveLength(1)
  })

  it('emits complete when maxLength is reached', async () => {
    const wrapper = mount(PinKeypad, { props: { maxLength: 4 } })
    for (const digit of ['1', '2', '3', '4']) {
      await keyButton(wrapper, digit).trigger('click')
    }
    expect(wrapper.emitted('complete')).toBeTruthy()
    expect(wrapper.emitted('complete')?.[0]).toEqual(['1234'])
  })

  it('clears and backspaces input', async () => {
    const wrapper = mount(PinKeypad, { props: { maxLength: 6 } })
    await keyButton(wrapper, '1').trigger('click')
    await keyButton(wrapper, '1').trigger('click')
    expect(wrapper.findAll('.dot.filled')).toHaveLength(2)

    const actionButtons = wrapper.findAll('button.btn')
    await actionButtons[1].trigger('click')
    expect(wrapper.findAll('.dot.filled')).toHaveLength(1)

    await actionButtons[0].trigger('click')
    expect(wrapper.findAll('.dot.filled')).toHaveLength(0)
  })

  it('does not exceed maxLength', async () => {
    const wrapper = mount(PinKeypad, { props: { maxLength: 2 } })
    await keyButton(wrapper, '1').trigger('click')
    await keyButton(wrapper, '1').trigger('click')
    await keyButton(wrapper, '1').trigger('click')
    expect(wrapper.findAll('.dot.filled')).toHaveLength(2)
    expect(wrapper.emitted('complete')?.length || 0).toBe(1)
  })
})
