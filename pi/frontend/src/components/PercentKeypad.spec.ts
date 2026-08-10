import { describe, expect, it } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import PercentKeypad from './PercentKeypad.vue'

function keyButton(wrapper: VueWrapper, digit: string) {
  return wrapper.findAll('button.key').find((b) => b.text() === digit)!
}

describe('PercentKeypad', () => {
  it('builds percent via digit keys and clamps at 100', async () => {
    const wrapper = mount(PercentKeypad, { props: { modelValue: 0 } })
    await keyButton(wrapper, '1').trigger('click')
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([1])
    await wrapper.setProps({ modelValue: 1 })
    await keyButton(wrapper, '2').trigger('click')
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([12])
    await wrapper.setProps({ modelValue: 12 })
    await keyButton(wrapper, '5').trigger('click')
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([100])
  })

  it('clears and backspaces', async () => {
    const wrapper = mount(PercentKeypad, { props: { modelValue: 25 } })
    await wrapper.findAll('button.btn')[1].trigger('click')
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([2])
    await wrapper.findAll('button.btn')[0].trigger('click')
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([0])
  })
})
