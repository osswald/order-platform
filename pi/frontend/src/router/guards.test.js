import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { setupRouterGuards } from './guards'
import * as store from '../store'
import { defaultBundle } from '../../tests/fixtures/bundle'
import { resetStore } from '../../tests/helpers/resetStore'

function buildRouter() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/events', name: 'events', component: { template: '<div/>' } },
      { path: '/login', name: 'login', component: { template: '<div/>' } },
      { path: '/registers', name: 'registers', component: { template: '<div/>' } },
      { path: '/admin-unlock', name: 'admin-unlock', component: { template: '<div/>' } },
      {
        path: '/order',
        name: 'order',
        component: { template: '<div/>' },
        meta: { requiresBundle: true, requiresEvent: true, requiresWaiter: true },
      },
      {
        path: '/register/:registerUuid',
        name: 'register-order',
        component: { template: '<div/>' },
        meta: { requiresBundle: true, requiresEvent: true, requiresRegister: true },
      },
      {
        path: '/admin',
        name: 'admin',
        component: { template: '<div/>' },
        meta: { requiresBundle: true, requiresAdmin: true },
      },
    ],
  })
  setupRouterGuards(router)
  return router
}

describe('setupRouterGuards', () => {
  beforeEach(() => {
    resetStore()
    vi.restoreAllMocks()
  })

  it('redirects to login when waiter is required but missing', async () => {
    store.bundle.value = defaultBundle()
    store.selectedEventId.value = 1
    const router = buildRouter()
    const result = await router.push('/order')
    expect(result).toBeUndefined()
    expect(router.currentRoute.value.name).toBe('login')
  })

  it('redirects to events when event is required but missing', async () => {
    store.bundle.value = defaultBundle()
    store.waiter.value = { uuid: 'w-1', name: 'Anna' }
    const router = buildRouter()
    await router.push('/order')
    expect(router.currentRoute.value.name).toBe('events')
  })

  it('redirects to registers when register session mismatches', async () => {
    store.bundle.value = defaultBundle()
    store.selectedEventId.value = 1
    store.registerSession.value = { uuid: 'other', name: 'Other' }
    const router = buildRouter()
    await router.push('/register/register-1')
    expect(router.currentRoute.value.name).toBe('registers')
  })

  it('redirects to admin-unlock when admin pin is required', async () => {
    store.bundle.value = { ...defaultBundle(), admin_pin_hashes: ['hash'] }
    store.adminUnlocked.value = false
    const router = buildRouter()
    await router.push('/admin')
    expect(router.currentRoute.value.name).toBe('admin-unlock')
  })

  it('redirects to events when bundle is unavailable after refresh', async () => {
    vi.spyOn(store, 'refreshBundle').mockResolvedValue(0)
    store.bundle.value = null
    const router = buildRouter()
    await router.push('/order')
    expect(router.currentRoute.value.name).toBe('events')
  })

  it('allows admin route without bundle when listed as bundle-free', async () => {
    vi.spyOn(store, 'refreshBundle').mockResolvedValue(0)
    store.bundle.value = null
    const router = buildRouter()
    await router.push('/admin')
    expect(router.currentRoute.value.name).toBe('admin')
  })
})
