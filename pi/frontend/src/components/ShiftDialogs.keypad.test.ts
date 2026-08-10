import { describe, expect, it, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import ShiftOpenDialog from './ShiftOpenDialog.vue'
import ShiftCloseDialog from './ShiftCloseDialog.vue'
import {
  shiftOpenDialogOpen,
  shiftOpenAmountChf,
  shiftCloseDialogOpen,
  shiftCloseAmountChf,
  shiftCloseExpectedLabel,
  shiftCloseError,
} from '@/composables/useShiftSession'

describe('shift dialogs money keypad', () => {
  beforeEach(() => {
    shiftOpenDialogOpen.value = false
    shiftOpenAmountChf.value = ''
    shiftCloseDialogOpen.value = false
    shiftCloseAmountChf.value = ''
    shiftCloseExpectedLabel.value = ''
    shiftCloseError.value = ''
  })

  it('ShiftOpenDialog uses MoneyKeypad instead of text input', async () => {
    shiftOpenDialogOpen.value = true
    shiftOpenAmountChf.value = '0.00'
    const wrapper = mount(ShiftOpenDialog, { attachTo: document.body })
    await nextTick()
    expect(wrapper.find('input.amount-input').exists()).toBe(false)
    expect(wrapper.find('.keypad').exists()).toBe(true)
    const keys = wrapper.findAll('button.key')
    await keys.find((b) => b.text() === '1')!.trigger('click')
    await keys.find((b) => b.text() === '2')!.trigger('click')
    await keys.find((b) => b.text() === '5')!.trigger('click')
    await keys.find((b) => b.text() === '0')!.trigger('click')
    expect(shiftOpenAmountChf.value).toBe('12.50')
    wrapper.unmount()
  })

  it('ShiftCloseDialog uses MoneyKeypad instead of text input', async () => {
    shiftCloseDialogOpen.value = true
    shiftCloseAmountChf.value = '10.00'
    shiftCloseExpectedLabel.value = '10.00'
    const wrapper = mount(ShiftCloseDialog, { attachTo: document.body })
    await nextTick()
    expect(wrapper.find('input.amount-input').exists()).toBe(false)
    expect(wrapper.find('.keypad').exists()).toBe(true)
    await wrapper.findAll('button.btn').find((b) => b.text() === 'C')!.trigger('click')
    const keys = wrapper.findAll('button.key')
    await keys.find((b) => b.text() === '5')!.trigger('click')
    await keys.find((b) => b.text() === '0')!.trigger('click')
    await keys.find((b) => b.text() === '0')!.trigger('click')
    expect(shiftCloseAmountChf.value).toBe('5.00')
    wrapper.unmount()
  })
})
