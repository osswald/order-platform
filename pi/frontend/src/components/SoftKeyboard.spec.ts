import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import SoftKeyboard from './SoftKeyboard.vue'

describe('SoftKeyboard', () => {
  it('inserts letters including German umlauts and ß', async () => {
    const wrapper = mount(SoftKeyboard, { props: { modelValue: '' } })
    await wrapper.findAll('button.kb-key').find((b) => b.text() === 'ä')!.trigger('click')
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['ä'])
    await wrapper.setProps({ modelValue: 'ä' })
    await wrapper.findAll('button.kb-key').find((b) => b.text() === 'ö')!.trigger('click')
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['äö'])
    await wrapper.setProps({ modelValue: 'äö' })
    await wrapper.findAll('button.kb-key').find((b) => b.text() === 'ü')!.trigger('click')
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['äöü'])
    await wrapper.setProps({ modelValue: 'äöü' })
    await wrapper.findAll('button.kb-key').find((b) => b.text() === 'ß')!.trigger('click')
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['äöüß'])
  })

  it('supports space, backspace, and shift for uppercase umlauts', async () => {
    const wrapper = mount(SoftKeyboard, { props: { modelValue: 'Hi' } })
    await wrapper.findAll('button.kb-key').find((b) => b.text() === 'Leer')!.trigger('click')
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['Hi '])
    await wrapper.setProps({ modelValue: 'Hi ' })
    await wrapper.findAll('button.kb-key').find((b) => b.text() === '⌫')!.trigger('click')
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['Hi'])
    await wrapper.setProps({ modelValue: '' })
    await wrapper.findAll('button.kb-key').find((b) => b.text() === '⇧')!.trigger('click')
    await wrapper.findAll('button.kb-key').find((b) => b.text() === 'Ä')!.trigger('click')
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['Ä'])
  })
})
