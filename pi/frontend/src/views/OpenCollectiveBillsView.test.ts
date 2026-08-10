import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { ref } from 'vue'
import type { EdgeBundleEvent } from '@/types/api'
import { COLLECTIVE_RETURN_TO_REGISTER } from '@/utils/collectiveReturnNav'

const push = vi.fn()
const replace = vi.fn()
const routeQuery = ref<Record<string, string>>({})
const eventRef = ref<EdgeBundleEvent | null>(null)
const showToast = vi.fn()

vi.mock('vue-router', () => ({
  useRoute: () => ({
    get query() {
      return routeQuery.value
    },
  }),
  useRouter: () => ({ push, replace }),
}))

vi.mock('@/api', () => ({
  api: vi.fn(),
}))

vi.mock('@/composables/useEventContext', () => ({
  useEventContext: () => ({
    event: eventRef,
    currency: ref('CHF'),
    showToast,
  }),
}))

import { api } from '@/api'
import OpenCollectiveBillsView from './OpenCollectiveBillsView.vue'

function baseEvent(): EdgeBundleEvent {
  return {
    id: 1,
    name: 'Sommerfest',
    currency: 'CHF',
    payment_mode: 'pay_later',
    status: 'prod',
  } as EdgeBundleEvent
}

describe('OpenCollectiveBillsView', () => {
  beforeEach(() => {
    push.mockReset()
    replace.mockReset()
    showToast.mockReset()
    routeQuery.value = {}
    eventRef.value = baseEvent()
    vi.mocked(api).mockReset()
    vi.mocked(api).mockResolvedValue({
      collective_bills: [{ id: 7, name: 'Personal', order_count: 1, total_cents: 500 }],
    })
  })

  it('backs to register hub when return query is present', async () => {
    routeQuery.value = {
      returnTo: COLLECTIVE_RETURN_TO_REGISTER,
      registerUuid: 'register-1',
    }
    const wrapper = mount(OpenCollectiveBillsView)
    await flushPromises()
    const back = wrapper.findAll('button').find((b) => b.text() === 'Zurück')
    expect(back).toBeTruthy()
    await back!.trigger('click')
    expect(push).toHaveBeenCalledWith({
      name: 'register-hub',
      params: { registerUuid: 'register-1' },
    })
  })

  it('backs to waiter hub when return query is absent', async () => {
    const wrapper = mount(OpenCollectiveBillsView)
    await flushPromises()
    const back = wrapper.findAll('button').find((b) => b.text() === 'Zurück')
    await back!.trigger('click')
    expect(push).toHaveBeenCalledWith({ name: 'hub' })
  })

  it('preserves return query when opening a bill', async () => {
    routeQuery.value = {
      returnTo: COLLECTIVE_RETURN_TO_REGISTER,
      registerUuid: 'register-1',
    }
    const wrapper = mount(OpenCollectiveBillsView)
    await flushPromises()
    await wrapper.find('.table-row').trigger('click')
    expect(push).toHaveBeenCalledWith({
      name: 'pay-collective',
      query: {
        id: '7',
        returnTo: COLLECTIVE_RETURN_TO_REGISTER,
        registerUuid: 'register-1',
      },
    })
  })

  it('opens in-app name sheet instead of window.prompt when creating a bill', async () => {
    window.prompt = vi.fn(() => 'should-not-be-used') as unknown as typeof window.prompt
    routeQuery.value = {
      returnTo: COLLECTIVE_RETURN_TO_REGISTER,
      registerUuid: 'register-1',
    }
    vi.mocked(api).mockImplementation(async (_path: string, init?: RequestInit) => {
      if (init?.method === 'POST') {
        return { id: 9, name: 'VIP' }
      }
      return {
        collective_bills: [{ id: 9, name: 'VIP', order_count: 0, total_cents: 0 }],
      }
    })
    const wrapper = mount(OpenCollectiveBillsView, {
      attachTo: document.body,
      global: { stubs: { teleport: true } },
    })
    await flushPromises()
    const createBtn = wrapper.findAll('button').find((b) => b.text().includes('Neue Sammelrechnung'))
    await createBtn!.trigger('click')
    await flushPromises()
    expect(window.prompt).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Name')
    expect(wrapper.find('.soft-keyboard').exists()).toBe(true)
    await wrapper.findAll('button.kb-key').find((b) => b.text() === '⇧')!.trigger('click')
    await wrapper.findAll('button.kb-key').find((b) => b.text() === 'V')!.trigger('click')
    await wrapper.findAll('button.kb-key').find((b) => b.text() === 'i')!.trigger('click')
    await wrapper.findAll('button.kb-key').find((b) => b.text() === 'p')!.trigger('click')
    const confirm = wrapper.find('button.confirm-btn')
    expect(confirm.exists()).toBe(true)
    await confirm.trigger('click')
    await flushPromises()
    expect(push).toHaveBeenCalledWith({
      name: 'pay-collective',
      query: {
        id: '9',
        returnTo: COLLECTIVE_RETURN_TO_REGISTER,
        registerUuid: 'register-1',
      },
    })
    wrapper.unmount()
  })
})
