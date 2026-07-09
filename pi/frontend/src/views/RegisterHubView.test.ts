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

import RegisterHubView from './RegisterHubView.vue'

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
})
