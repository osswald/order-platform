import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { ref } from 'vue'

const push = vi.fn()
const replace = vi.fn()
const isAndroidApp = vi.fn(() => false)
const getAndroidAppInfo = vi.fn((): ReturnType<typeof import('@/utils/androidAppInfo').getAndroidAppInfo> => ({
  status: 'unavailable',
}))
const checkTapToPayAdminStatus = vi.fn(
  (_force?: boolean): ReturnType<typeof import('@/utils/taptoPayStatus').checkTapToPayAdminStatus> => ({
    code: 'unavailable',
  }),
)
const tapToPayAdminStatusLabel = vi.fn((status: { code: string }) => {
  const labels: Record<string, string> = {
    checking: 'prüfen…',
    ready: 'bereit',
    ready_simulated: 'bereit (simuliert)',
    location_missing: 'Standort fehlt',
    unsupported: 'nicht unterstützt',
    error: 'Fehler',
    unavailable: 'nicht verfügbar',
  }
  return labels[status.code] ?? 'nicht verfügbar'
})

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
  useAppVersion: () => ({ label: 'v1.0.0 (test)' }),
}))

vi.mock('@/composables/useBundle', () => ({
  useBundle: () => ({
    bundle: ref({ events: [{ id: 1, name: 'Test Event' }] }),
  }),
}))

vi.mock('@/utils/androidAppInfo', () => ({
  getAndroidAppInfo: () => getAndroidAppInfo(),
}))

vi.mock('@/utils/taptoPayStatus', () => ({
  checkTapToPayAdminStatus: (force?: boolean) => checkTapToPayAdminStatus(force),
  tapToPayAdminStatusLabel: (status: { code: string }) => tapToPayAdminStatusLabel(status),
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
    getAndroidAppInfo.mockReset()
    getAndroidAppInfo.mockReturnValue({ status: 'unavailable' })
    checkTapToPayAdminStatus.mockReset()
    checkTapToPayAdminStatus.mockReturnValue({ code: 'unavailable' })
    tapToPayAdminStatusLabel.mockClear()
    vi.mocked(api).mockImplementation(async (path: string) => {
      if (path === '/health') {
        return { status: 'ok', version: '2.0.0', build_time: '202607201100' }
      }
      return {
        configured: true,
        can_unpair: true,
      }
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

  it('shows frontend and backend version labels', async () => {
    const wrapper = mountHub()
    await flushPromises()
    expect(wrapper.text()).toContain('App v1.0.0 (test)')
    expect(wrapper.text()).toContain('Pi v2.0.0 (202607201100)')
  })

  it('shows dash for backend version when health fails', async () => {
    vi.mocked(api).mockImplementation(async (path: string) => {
      if (path === '/health') throw new Error('offline')
      return { configured: true, can_unpair: false }
    })
    const wrapper = mountHub()
    await flushPromises()
    expect(wrapper.text()).toContain('App v1.0.0 (test)')
    expect(wrapper.text()).toContain('Pi —')
  })

  it('hides Android version and Tap to Pay lines off Android', async () => {
    const wrapper = mountHub()
    await flushPromises()
    expect(wrapper.text()).not.toContain('Android ')
    expect(wrapper.text()).not.toContain('Tap to Pay:')
    expect(checkTapToPayAdminStatus).not.toHaveBeenCalled()
  })

  it('shows Android version line only when bridge returns a version', async () => {
    isAndroidApp.mockReturnValue(true)
    getAndroidAppInfo.mockReturnValue({
      status: 'ok',
      versionName: '1.5.10',
      versionCode: 10510,
    })
    checkTapToPayAdminStatus.mockReturnValue({ code: 'ready' })
    const wrapper = mountHub()
    await flushPromises()
    expect(wrapper.text()).toContain('Android v1.5.10')
  })

  it('shows Tap to Pay checking then ready on Android Admin open', async () => {
    isAndroidApp.mockReturnValue(true)
    getAndroidAppInfo.mockReturnValue({ status: 'unavailable' })
    checkTapToPayAdminStatus.mockReturnValue({ code: 'ready' })
    const wrapper = mountHub()
    expect(wrapper.text()).toContain('Tap to Pay: prüfen…')
    await flushPromises()
    expect(wrapper.text()).toContain('Tap to Pay: bereit')
    expect(checkTapToPayAdminStatus).toHaveBeenCalledWith(true)
  })

  it('shows location_missing Tap to Pay status', async () => {
    isAndroidApp.mockReturnValue(true)
    checkTapToPayAdminStatus.mockReturnValue({ code: 'location_missing' })
    const wrapper = mountHub()
    await flushPromises()
    expect(wrapper.text()).toContain('Tap to Pay: Standort fehlt')
  })
})
