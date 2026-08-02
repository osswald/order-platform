import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { computed, ref } from 'vue'
import type { EdgeBundleEvent } from '@/types/api'

const push = vi.fn()
const replace = vi.fn()
const eventRef = ref<EdgeBundleEvent | null>(null)
const registerRef = ref<{ uuid: string; name: string } | null>(null)
const ensureReachable = vi.fn(async () => true)
const status = ref<'unknown' | 'reachable' | 'unreachable'>('reachable')
const probing = ref(false)

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

vi.mock('@/composables/usePiConnectivity', () => ({
  usePiConnectivity: () => ({
    status,
    probing,
    unreachable: computed(() => status.value === 'unreachable'),
    ensureReachable,
    probeNow: vi.fn(async () => status.value === 'reachable'),
  }),
}))

import { api } from '@/api'
import RegisterHubView from './RegisterHubView.vue'
import { COLLECTIVE_RETURN_TO_REGISTER } from '@/utils/collectiveReturnNav'

function baseEvent(statusValue: string): EdgeBundleEvent {
  return {
    id: 1,
    name: 'Sommerfest',
    currency: 'CHF',
    payment_mode: 'pay_later',
    status: statusValue,
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
      { path: '/connection-setup', name: 'connection-setup', component: { template: '<div/>' } },
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
    ensureReachable.mockReset()
    ensureReachable.mockResolvedValue(true)
    status.value = 'reachable'
    probing.value = false
    eventRef.value = baseEvent('test')
    registerRef.value = { uuid: 'register-1', name: 'Kasse 1' }
    vi.mocked(api).mockResolvedValue({ orders: [] })
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

  it('shows unreachable banner when Pi is unreachable', async () => {
    status.value = 'unreachable'
    const wrapper = mountHub()
    await flushPromises()
    expect(wrapper.text()).toContain('Keine Verbindung zur Kasse')
  })

  it('navigates to Sammelrechnungen with register return query', async () => {
    const wrapper = mountHub()
    await flushPromises()
    const buttons = wrapper.findAll('button')
    const collectiveBtn = buttons.find((b) => b.text().includes('Sammelrechnungen'))
    expect(collectiveBtn).toBeTruthy()
    await collectiveBtn!.trigger('click')
    await flushPromises()
    expect(ensureReachable).toHaveBeenCalled()
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
          pickup_codes: ['A1', 'A2'],
          item_count: 2,
          total_cents: 800,
          created_at: '2026-07-18T12:00:00Z',
        },
      ],
    })
    const wrapper = mountHub()
    await flushPromises()
    expect(wrapper.text()).toContain('Offene Bestellungen')
    expect(wrapper.text()).toContain('Pickup A1, A2')
    const orderBtn = wrapper.find('.order-row')
    await orderBtn.trigger('click')
    await flushPromises()
    expect(push).toHaveBeenCalledWith({
      name: 'register-pay',
      params: { registerUuid: 'register-1', orderId: '11' },
    })
  })

  it('blocks Neue Bestellung when ensureReachable fails', async () => {
    ensureReachable.mockResolvedValue(false)
    status.value = 'unreachable'
    const wrapper = mountHub()
    await flushPromises()
    const btn = wrapper.findAll('button').find((b) => b.text().includes('Neue Bestellung'))
    await btn!.trigger('click')
    await flushPromises()
    expect(push).not.toHaveBeenCalled()
  })

  it('blocks Sammelrechnungen and resume when unreachable', async () => {
    ensureReachable.mockResolvedValue(false)
    status.value = 'unreachable'
    vi.mocked(api).mockResolvedValueOnce({
      orders: [
        {
          local_order_id: 11,
          pickup_code: 'A1',
          pickup_codes: ['A1'],
          item_count: 1,
          total_cents: 400,
          created_at: '2026-07-18T12:00:00Z',
        },
      ],
    })
    const wrapper = mountHub()
    await flushPromises()
    const collectiveBtn = wrapper.findAll('button').find((b) => b.text().includes('Sammelrechnungen'))
    await collectiveBtn!.trigger('click')
    await flushPromises()
    expect(push).not.toHaveBeenCalled()

    await wrapper.find('.order-row').trigger('click')
    await flushPromises()
    expect(push).not.toHaveBeenCalled()
  })

  it('navigates Neue Bestellung when warm ensureReachable succeeds', async () => {
    const wrapper = mountHub()
    await flushPromises()
    const btn = wrapper.findAll('button').find((b) => b.text().includes('Neue Bestellung'))
    await btn!.trigger('click')
    await flushPromises()
    expect(ensureReachable).toHaveBeenCalled()
    expect(push).toHaveBeenCalledWith({ name: 'register-order' })
  })
})
