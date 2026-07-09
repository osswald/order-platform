import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { ref } from 'vue'
import { bundleCopy, defaultBundle } from '@tests/fixtures/bundle'
import type { EdgeBundleResponse, EdgeBundleEvent } from '@/types/api'

const bundleRef = ref<EdgeBundleResponse | null>(null)
const refreshBundle = vi.fn(async () => 0)

vi.mock('@/composables/useBundle', () => ({
  useBundle: () => ({
    bundle: bundleRef,
    isBundleReady: ref(true),
    refreshBundle,
    showToast: vi.fn(),
    selectedEventId: ref(null),
  }),
}))

vi.mock('@/composables/useAdminSession', () => ({
  useAdminSession: () => ({
    adminUnlocked: ref(false),
    requiresPin: ref(false),
    setAdminUnlocked: vi.fn(),
  }),
}))

vi.mock('@/composables/useWaiterSession', () => ({
  useWaiterSession: () => ({
    setWaiter: vi.fn(),
  }),
}))

vi.mock('@/store', () => ({
  setRegisterSession: vi.fn(),
}))

import EventsView from './EventsView.vue'

function eventsBundle(testStatus: string, prodStatus: string): EdgeBundleResponse {
  const bundle = bundleCopy(defaultBundle())
  const testEvent: EdgeBundleEvent = {
    id: 1,
    name: 'Test Event',
    currency: 'CHF',
    payment_mode: 'pay_later',
    status: testStatus,
    configuration: { stations: [] },
  } as EdgeBundleEvent
  const prodEvent: EdgeBundleEvent = {
    id: 2,
    name: 'Prod Event',
    currency: 'CHF',
    payment_mode: 'pay_later',
    status: prodStatus,
    configuration: { stations: [] },
  } as EdgeBundleEvent
  bundle.events = [testEvent, prodEvent]
  return bundle
}

function mountEvents() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/events', name: 'events', component: { template: '<div/>' } },
      { path: '/admin', name: 'admin', component: { template: '<div/>' } },
    ],
  })
  return mount(EventsView, { global: { plugins: [router] } })
}

describe('EventsView', () => {
  beforeEach(() => {
    refreshBundle.mockClear()
    bundleRef.value = eventsBundle('test', 'prod')
  })

  it('shows TESTBETRIEB pill only on test events in the list', async () => {
    const wrapper = mountEvents()
    await flushPromises()
    const pills = wrapper.findAll('.test-pill')
    expect(pills).toHaveLength(1)
    expect(pills[0].text()).toBe('TESTBETRIEB')
    expect(wrapper.text()).toContain('Test Event')
    expect(wrapper.text()).toContain('Prod Event')
  })

  it('hides TESTBETRIEB pills when no events are in test mode', async () => {
    bundleRef.value = eventsBundle('prod', 'prod')
    const wrapper = mountEvents()
    await flushPromises()
    expect(wrapper.findAll('.test-pill')).toHaveLength(0)
  })
})
