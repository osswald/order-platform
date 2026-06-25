import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { ref } from 'vue'
import { bundleWithRegisters } from '@tests/fixtures/bundle'
import type { EdgeBundleEvent } from '@/types/api'

const bundleRef = ref(bundleWithRegisters())

vi.mock('@/composables/useBundle', () => ({
  useBundle: () => ({
    bundle: bundleRef,
    busy: ref(false),
    showToast: vi.fn(),
    selectedEventId: ref(1),
  }),
}))

import AdminOperationsHubView from './AdminOperationsHubView.vue'

function mountHub() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/admin/operations', name: 'admin-operations', component: { template: '<div/>' } },
      { path: '/admin/operations/test-print', name: 'admin-operations-test-print', component: { template: '<div/>' } },
      { path: '/admin/operations/kitchen', name: 'admin-operations-kitchen', component: { template: '<div/>' } },
      { path: '/admin/operations/pickup', name: 'admin-operations-pickup', component: { template: '<div/>' } },
      { path: '/admin/operations/display', name: 'admin-operations-display', component: { template: '<div/>' } },
    ],
  })
  return mount(AdminOperationsHubView, { global: { plugins: [router] } })
}

describe('AdminOperationsHubView', () => {
  beforeEach(() => {
    const base = bundleWithRegisters()
    const ev = base.events![0] as EdgeBundleEvent
    ev.kitchen_monitors_enabled = true
    ev.configuration = {
      ...ev.configuration,
      kitchen_monitors: [{ printer_appliance_id: 1, label: 'Grill', sort_order: 0 }],
    }
    bundleRef.value = base
  })

  it('shows topic tiles for operations areas', async () => {
    const wrapper = mountHub()
    await flushPromises()
    expect(wrapper.find('.admin-topic-grid').exists()).toBe(true)
    expect(wrapper.text()).toContain('Testdruck')
    expect(wrapper.text()).toContain('Küchenmonitor')
    expect(wrapper.text()).toContain('Pickup Screen')
    expect(wrapper.text()).toContain('Kundendisplay')
    expect(wrapper.findAll('.admin-topic-btn').length).toBeGreaterThanOrEqual(2)
  })
})
