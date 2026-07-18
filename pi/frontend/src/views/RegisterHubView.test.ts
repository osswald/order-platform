import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { ref } from 'vue'
import type { EdgeBundleEvent } from '@/types/api'

const push = vi.fn()
const replace = vi.fn()
const eventRef = ref<EdgeBundleEvent | null>(null)
const registerRef = ref<{ uuid: string; name: string } | null>(null)

vi.mock('@/composables/useCart', () => ({
  useCart: () => ({
    clearCart: vi.fn(),
  }),
}))

vi.mock('@/composables/useRegisterSession', () => ({
  useRegisterSession: () => ({
    setRegisterSession: vi.fn(),
  }),
}))

vi.mock('@/composables/useShiftSession', () => ({
  ensureShiftForSubject: vi.fn(async () => undefined),
  maybeEndShiftOnSwitch: vi.fn(async () => true),
}))

vi.mock('@/composables/useRegisterDisplay', () => ({
  useRegisterDisplay: () => ({
    register: registerRef,
    event: eventRef,
    setDisplayIdle: vi.fn(),
    clearPickupHold: vi.fn(),
    orderRoute: () => ({ name: 'register-order' }),
  }),
}))

vi.mock('@/api', () => ({
  api: vi.fn(async () => ({ orders: [] })),
}))

vi.mock('@/composables/useEventContext', () => ({
  useEventContext: () => ({
    currency: ref('CHF'),
  }),
}))

import { api } from '@/api'
import RegisterHubView from './RegisterHubView.vue'
import { COLLECTIVE_RETURN_TO_REGISTER } from '@/utils/collectiveReturnNav'

function baseEvent(status: string): EdgeBundleEvent {
  return {
    id: 1,
    name: 'Sommerfest',
    currency: 'CHF',
    payment_mode: 'pay_later',
    status,
    configuration: {
      cash_registers: [{ uuid: 'register-1', name: 'Kasse 1' }],
    },
  } as EdgeBundleEvent
}

function mountHub() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/register/:registerUuid', name: 'register-hub', component: { template: '<div/>' } },
      { path: '/registers', name: 'registers', component: { template: '<div/>' } },
      { path: '/events', name: 'events', component: { template: '<div/>' } },
    ],
  })
  router.push = push
  router.replace = replace
  return mount(RegisterHubView, {
    global: {
      plugins: [router],
    },
  })
}

describe('RegisterHubView', () => {
  beforeEach(() => {
    push.mockReset()
    replace.mockReset()
    eventRef.value = baseEvent('test')
    registerRef.value = { uuid: 'register-1', name: 'Kasse 1' }
  })

  it('shows TESTBETRIEB pill when event status is test', async () => {
    const wrapper = mountHub()
    await flushPromises()
    const pill = wrapper.find('.test-pill')
    expect(pill.exists()).toBe(true)
    expect(pill.text()).toBe('TESTBETRIEB')
  })

  it('hides TESTBETRIEB pill when event status is prod', async () => {
    eventRef.value = baseEvent('prod')
    const wrapper = mountHub()
    await flushPromises()
    expect(wrapper.find('.test-pill').exists()).toBe(false)
  })

  it('navigates to Sammelrechnungen with register return query', async () => {
    const wrapper = mountHub()
    await flushPromises()
    const buttons = wrapper.findAll('button')
    const collectiveBtn = buttons.find((b) => b.text().includes('Sammelrechnungen'))
    expect(collectiveBtn).toBeTruthy()
    await collectiveBtn!.trigger('click')
    expect(push).toHaveBeenCalledWith({
      name: 'collective-open',
      query: {
        returnTo: COLLECTIVE_RETURN_TO_REGISTER,
        registerUuid: 'register-1',
      },
    })
  })

  it('still lists open orders for resume payment', async () => {
    vi.mocked(api).mockResolvedValueOnce({
      orders: [
        {
          local_order_id: 11,
          pickup_code: 'A1',
          item_count: 2,
          total_cents: 800,
          created_at: '2026-07-18T12:00:00Z',
        },
      ],
    })
    const wrapper = mountHub()
    await flushPromises()
    expect(wrapper.text()).toContain('Offene Bestellungen')
    expect(wrapper.text()).toContain('Pickup A1')
    const orderBtn = wrapper.find('.order-row')
    await orderBtn.trigger('click')
    expect(push).toHaveBeenCalledWith({
      name: 'register-pay',
      params: { registerUuid: 'register-1', orderId: '11' },
    })
  })
})
