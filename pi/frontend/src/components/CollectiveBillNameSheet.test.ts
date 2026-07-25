import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import CollectiveBillNameSheet from './CollectiveBillNameSheet.vue'

function mountSheet(props: Record<string, unknown> = {}) {
  return mount(CollectiveBillNameSheet, {
    props: { open: true, ...props },
    attachTo: document.body,
    global: { stubs: { teleport: true } },
  })
}

describe('CollectiveBillNameSheet', () => {
  it('emits confirm with trimmed name', async () => {
    const wrapper = mountSheet({ confirmLabel: 'Erstellen und zuordnen' })
    await flushPromises()
    await wrapper.find('input.text-input').setValue('  Personal  ')
    const btn = wrapper.findAll('button').find((b) => b.text().includes('Erstellen und zuordnen'))
    expect(btn).toBeTruthy()
    await btn!.trigger('click')
    expect(wrapper.emitted('confirm')?.[0]).toEqual(['Personal'])
    wrapper.unmount()
  })

  it('disables confirm when name is empty and enables when a name is entered', async () => {
    const wrapper = mountSheet()
    await flushPromises()
    const btn = wrapper.find('button.confirm-btn')
    expect(btn.attributes('disabled')).toBeDefined()
    await wrapper.find('input.text-input').setValue('Personal')
    expect(wrapper.find('button.confirm-btn').attributes('disabled')).toBeUndefined()
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
