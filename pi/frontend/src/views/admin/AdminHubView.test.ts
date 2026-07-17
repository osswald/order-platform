import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { ref } from 'vue'

const push = vi.fn()
const replace = vi.fn()
const isAndroidApp = vi.fn(() => false)

vi.mock('@/api', () => ({
  api: vi.fn(),
  isAndroidApp: () => isAndroidApp(),
}))

vi.mock('@/composables/useAdminSession', () => ({
  useAdminSession: () => ({
    clearAdminSession: vi.fn(),
  }),
}))

vi.mock('@/composables/useAppVersion', () => ({
  useAppVersion: () => ({ label: 'test' }),
}))

vi.mock('@/composables/useBundle', () => ({
  useBundle: () => ({
    bundle: ref({ events: [{ id: 1, name: 'Test Event' }] }),
  }),
}))

import { api } from '@/api'
import AdminHubView from './AdminHubView.vue'

function mountHub() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/admin', name: 'admin', component: { template: '<div/>' } },
      { path: '/admin/sync', name: 'admin-sync', component: { template: '<div/>' } },
      { path: '/admin/operations', name: 'admin-operations', component: { template: '<div/>' } },
      { path: '/admin/unpair', name: 'admin-unpair', component: { template: '<div/>' } },
      { path: '/android/printer', name: 'android-printer', component: { template: '<div/>' } },
    ],
  })
  router.push = push
  router.replace = replace
  return mount(AdminHubView, { global: { plugins: [router] } })
}

describe('AdminHubView', () => {
  beforeEach(() => {
    vi.mocked(api).mockReset()
    push.mockReset()
    replace.mockReset()
    isAndroidApp.mockReturnValue(false)
    vi.mocked(api).mockResolvedValue({
      configured: true,
      can_unpair: true,
    })
  })

  it('shows at least two topic tiles side by side', async () => {
    const wrapper = mountHub()
    await flushPromises()
    const tiles = wrapper.findAll('.admin-topic-btn')
    expect(tiles.length).toBeGreaterThanOrEqual(2)
    expect(wrapper.find('.admin-topic-grid').exists()).toBe(true)
    expect(wrapper.text()).toContain('Synchronisation')
    expect(wrapper.text()).toContain('Betrieb')
  })

  it('shows Bluetooth tile only on Android', async () => {
    isAndroidApp.mockReturnValue(true)
    const wrapper = mountHub()
    await flushPromises()
    expect(wrapper.text()).toContain('Bluetooth Drucker')
  })

  it('hides unpair tile when unpair is not allowed', async () => {
    vi.mocked(api).mockResolvedValue({
      configured: true,
      can_unpair: false,
    })
    const wrapper = mountHub()
    await flushPromises()
    expect(wrapper.text()).not.toContain('Gerät entkoppeln')
  })

  it('shows unpair tile when allowed', async () => {
    const wrapper = mountHub()
    await flushPromises()
    expect(wrapper.text()).toContain('Gerät entkoppeln')
  })
})
