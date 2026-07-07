import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { ref } from 'vue'
import type { EdgeBundleEvent } from '@/types/api'

const push = vi.fn()
const eventRef = ref<EdgeBundleEvent | null>(null)
const waiterRef = ref({ uuid: 'w-1', name: 'Anna' })
const selectedEventIdRef = ref(1)

vi.mock('@/api', () => ({
  isAndroidApp: () => false,
}))

vi.mock('@/composables/useEventContext', () => ({
  useEventContext: () => ({
    event: eventRef,
    waiter: waiterRef,
    setWaiter: vi.fn(),
    selectedEventId: selectedEventIdRef,
  }),
}))

vi.mock('@/composables/useStationPrintFailures', () => ({
  useStationPrintFailures: () => ({
    failedCount: ref(0),
    loadFailedJobs: vi.fn(),
  }),
}))

vi.mock('@/composables/useShiftSession', () => ({
  maybeEndShiftOnSwitch: vi.fn(async () => true),
}))

import WaiterHubView from './WaiterHubView.vue'

function baseEvent(status: string): EdgeBundleEvent {
  return {
    id: 1,
    name: 'Sommerfest',
    currency: 'CHF',
    payment_mode: 'pay_later',
    status,
  } as EdgeBundleEvent
}

function mountHub() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/hub', name: 'hub', component: { template: '<div/>' } },
      { path: '/events', name: 'events', component: { template: '<div/>' } },
      { path: '/login', name: 'login', component: { template: '<div/>' } },
    ],
  })
  router.push = push
  return mount(WaiterHubView, { global: { plugins: [router] } })
}

describe('WaiterHubView', () => {
  beforeEach(() => {
    push.mockReset()
    eventRef.value = baseEvent('test')
    waiterRef.value = { uuid: 'w-1', name: 'Anna' }
    selectedEventIdRef.value = 1
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
