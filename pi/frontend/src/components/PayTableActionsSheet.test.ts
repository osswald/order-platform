import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { ref } from 'vue'
import type { EdgeBundleEvent } from '@/types/api'

const showToast = vi.fn()

vi.mock('@/api', () => ({
  api: vi.fn(),
}))

vi.mock('@/composables/useEventContext', () => ({
  useEventContext: () => ({
    event: ref({ id: 1, payment_mode: 'pay_later' } as EdgeBundleEvent),
    currency: ref('CHF'),
    showToast,
  }),
}))

import { api } from '@/api'
import PayTableActionsSheet from './PayTableActionsSheet.vue'

describe('PayTableActionsSheet', () => {
  beforeEach(() => {
    showToast.mockReset()
    vi.mocked(api).mockReset()
    window.prompt = vi.fn(() => 'should-not-be-used') as unknown as typeof window.prompt
  })

  it('opens shared name sheet for Neue Sammelrechnung (same UX as hub create)', async () => {
    vi.mocked(api).mockImplementation(async (path: string) => {
      if (String(path).includes('/collective-bills/open')) {
        return { collective_bills: [] }
      }
      return { name: 'VIP' }
    })
    const wrapper = mount(PayTableActionsSheet, {
      props: {
        open: true,
        eventId: 1,
        fromTable: 2,
        selections: [{ kind: 'article', article_id: 1, note: '', qty: 1 }],
      },
      attachTo: document.body,
      global: { stubs: { teleport: true } },
    })
    await flushPromises()
    const collectiveBtn = wrapper.findAll('button').find((b) => b.text().includes('Sammelrechnung'))
    await collectiveBtn!.trigger('click')
    await flushPromises()
    const newBtn = wrapper.findAll('button').find((b) => b.text().includes('Neue Sammelrechnung'))
    await newBtn!.trigger('click')
    await flushPromises()
    expect(window.prompt).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Name')
    expect(wrapper.find('button.confirm-btn').text()).toContain('Erstellen und zuordnen')
    expect(wrapper.find('.soft-keyboard').exists()).toBe(true)
    await wrapper.findAll('button.kb-key').find((b) => b.text() === '⇧')!.trigger('click')
    await wrapper.findAll('button.kb-key').find((b) => b.text() === 'V')!.trigger('click')
    await wrapper.findAll('button.kb-key').find((b) => b.text() === '⇧')!.trigger('click')
    await wrapper.findAll('button.kb-key').find((b) => b.text() === 'I')!.trigger('click')
    await wrapper.findAll('button.kb-key').find((b) => b.text() === '⇧')!.trigger('click')
    await wrapper.findAll('button.kb-key').find((b) => b.text() === 'P')!.trigger('click')
    await wrapper.find('button.confirm-btn').trigger('click')
    await flushPromises()
    expect(api).toHaveBeenCalledWith(
      '/v1/tables/2/assign-collective',
      expect.objectContaining({ method: 'POST' }),
    )
    const body = JSON.parse(
      String(vi.mocked(api).mock.calls.find((c) => c[1]?.method === 'POST')?.[1]?.body),
    )
    expect(body.new_name).toBe('VIP')
    wrapper.unmount()
  })
})
