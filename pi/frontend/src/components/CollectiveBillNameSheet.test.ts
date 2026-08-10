import { describe, expect, it, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import CollectiveBillNameSheet from './CollectiveBillNameSheet.vue'

const isAndroidApp = vi.fn(() => false)

vi.mock('@/api/base', () => ({
  isAndroidApp: () => isAndroidApp(),
}))

function mountSheet(props: Record<string, unknown> = {}) {
  return mount(CollectiveBillNameSheet, {
    props: { open: true, ...props },
    attachTo: document.body,
    global: { stubs: { teleport: true } },
  })
}

describe('CollectiveBillNameSheet', () => {
  beforeEach(() => {
    isAndroidApp.mockReturnValue(false)
  })

  it('uses soft keyboard on non-Android and confirms typed name', async () => {
    const wrapper = mountSheet()
    await flushPromises()
    expect(wrapper.find('input.text-input').exists()).toBe(false)
    expect(wrapper.find('.soft-keyboard').exists()).toBe(true)
    await wrapper.findAll('button.kb-key').find((b) => b.text() === 'a')!.trigger('click')
    await wrapper.findAll('button.kb-key').find((b) => b.text() === 'b')!.trigger('click')
    await flushPromises()
    expect(wrapper.find('button.confirm-btn').attributes('disabled')).toBeUndefined()
    await wrapper.find('button.confirm-btn').trigger('click')
    expect(wrapper.emitted('confirm')?.[0]).toEqual(['ab'])
    wrapper.unmount()
  })

  it('uses native input on Android', async () => {
    isAndroidApp.mockReturnValue(true)
    const wrapper = mountSheet()
    await flushPromises()
    expect(wrapper.find('input.text-input').exists()).toBe(true)
    expect(wrapper.find('.soft-keyboard').exists()).toBe(false)
    await wrapper.find('input.text-input').setValue('  Personal  ')
    await wrapper.find('button.confirm-btn').trigger('click')
    expect(wrapper.emitted('confirm')?.[0]).toEqual(['Personal'])
    wrapper.unmount()
  })

  it('disables confirm when name is empty and enables when a name is entered', async () => {
    isAndroidApp.mockReturnValue(true)
    const wrapper = mountSheet()
    await flushPromises()
    const btn = wrapper.find('button.confirm-btn')
    expect(btn.attributes('disabled')).toBeDefined()
    await wrapper.find('input.text-input').setValue('Personal')
    await flushPromises()
    expect(wrapper.find('button.confirm-btn').attributes('disabled')).toBeUndefined()
    await wrapper.find('input.text-input').setValue('')
    await flushPromises()
    expect(wrapper.find('button.confirm-btn').attributes('disabled')).toBeDefined()
    wrapper.unmount()
  })

  it('emits close on back', async () => {
    const wrapper = mountSheet()
    await flushPromises()
    const back = wrapper.findAll('button').find((b) => b.text().includes('Zurück'))
    await back!.trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
    wrapper.unmount()
  })
})
