import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { nextTick, ref } from 'vue'
import { bundleWithRegisters } from '@tests/fixtures/bundle'
import type { EdgeBundleEvent, EdgeBundleResponse } from '@/types/api'

const showToast = vi.fn()
const bundleRef = ref<EdgeBundleResponse>(bundleWithRegisters())

vi.mock('@/composables/useBundle', () => ({
  useBundle: () => ({
    bundle: bundleRef,
    busy: ref(false),
    showToast,
    selectedEventId: ref(1),
  }),
}))

const apiMock = vi.fn()
vi.mock('@/api', () => ({
  api: (...args: unknown[]) => apiMock(...args),
  isAndroidApp: () => false,
}))

import AdminOperationsHubView from './AdminOperationsHubView.vue'
import AdminOperationsLoadTestView from './AdminOperationsLoadTestView.vue'

function testBundle(status: string): EdgeBundleResponse {
  const base = bundleWithRegisters()
  const ev = base.events![0] as EdgeBundleEvent
  ev.status = status
  ev.kitchen_monitors_enabled = true
  ev.configuration = {
    ...ev.configuration,
    event_waiters: [
      { uuid: 'w-1', name: 'Anna' },
      { uuid: 'w-2', name: 'Ben' },
    ],
    kitchen_monitors: [{ printer_appliance_id: 1, label: 'Grill', sort_order: 0 }],
  }
  return base
}

function mountHub() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/admin/operations', name: 'admin-operations', component: { template: '<div/>' } },
      {
        path: '/admin/operations/test-print',
        name: 'admin-operations-test-print',
        component: { template: '<div/>' },
      },
      {
        path: '/admin/operations/kitchen',
        name: 'admin-operations-kitchen',
        component: { template: '<div/>' },
      },
      {
        path: '/admin/operations/pickup',
        name: 'admin-operations-pickup',
        component: { template: '<div/>' },
      },
      {
        path: '/admin/operations/display',
        name: 'admin-operations-display',
        component: { template: '<div/>' },
      },
      {
        path: '/admin/operations/load-test',
        name: 'admin-operations-load-test',
        component: { template: '<div/>' },
      },
    ],
  })
  return mount(AdminOperationsHubView, { global: { plugins: [router] } })
}

function mountLoadTest() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'admin-operations', component: { template: '<div/>' } },
      {
        path: '/load-test',
        name: 'admin-operations-load-test',
        component: AdminOperationsLoadTestView,
      },
    ],
  })
  return mount(AdminOperationsLoadTestView, { global: { plugins: [router] } })
}

describe('Lasttest admin UI', () => {
  beforeEach(() => {
    showToast.mockReset()
    apiMock.mockReset()
    apiMock.mockResolvedValue({ state: 'idle', placed: 0, failed: 0, receipts_printed: 0 })
    bundleRef.value = testBundle('test')
  })

  it('shows Lasttest tile only for test events', async () => {
    const wrapper = mountHub()
    await flushPromises()
    expect(wrapper.text()).toContain('Lasttest')

    bundleRef.value = testBundle('prod')
    await nextTick()
    await flushPromises()
    expect(wrapper.text()).not.toContain('Lasttest')
  })

  it('shows form caps from event waiters and registers', async () => {
    const wrapper = mountLoadTest()
    await flushPromises()
    expect(wrapper.text()).toContain('Lasttest')
    expect(wrapper.text()).toContain('von 2 verfügbar')
    expect(wrapper.text()).toContain('von 1 verfügbar')
    expect(wrapper.findAll('input[type="number"]').length).toBeGreaterThanOrEqual(4)
  })

  it('hides form for non-test events', async () => {
    bundleRef.value = testBundle('config')
    const wrapper = mountLoadTest()
    await flushPromises()
    expect(wrapper.text()).toContain('Nur für Events im Status Testbetrieb')
    expect(wrapper.find('button.primary').exists()).toBe(false)
  })

  it('starts load test via API', async () => {
    apiMock
      .mockResolvedValueOnce({ state: 'idle' })
      .mockResolvedValueOnce({
        state: 'running',
        placed: 0,
        failed: 0,
        receipts_printed: 0,
        current_burst: 0,
        total_bursts: 10,
        config: { waiter_count: 1, cash_register_count: 0, actors_per_burst: 1 },
      })
    const wrapper = mountLoadTest()
    await flushPromises()
    await wrapper.find('button.primary').trigger('click')
    await flushPromises()
    expect(apiMock).toHaveBeenCalledWith(
      '/v1/load-test/start',
      expect.objectContaining({ method: 'POST' }),
    )
    expect(showToast).toHaveBeenCalled()
  })
})
