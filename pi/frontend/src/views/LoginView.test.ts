import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { nextTick } from 'vue'
import type { EdgeBundleEvent } from '@/types/api'
import { resetStore } from '@tests/helpers/resetStore'
import * as store from '@/store'

const ensureShiftForSubject = vi.fn(async () => undefined)

vi.mock('@/composables/useShiftSession', () => ({
  ensureShiftForSubject: (...args: unknown[]) => ensureShiftForSubject(...args),
}))

vi.mock('@/utils/ediModemLogin', () => ({
  shouldRunEdiModemHandshake: () => false,
  awaitAndroidModemHandshake: vi.fn(async () => false),
}))

import LoginView from './LoginView.vue'

function waiterEvent(): EdgeBundleEvent {
  return {
    id: 1,
    name: 'Sommerfest',
    currency: 'CHF',
    payment_mode: 'pay_later',
    payment_types: ['cash'],
    configuration: {
      event_waiters: [{ uuid: 'waiter-1', name: 'Anna', pin: '1234' }],
    },
  } as EdgeBundleEvent
}

async function mountLogin() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'login', component: LoginView },
      { path: '/hub', name: 'hub', component: { template: '<div/>' } },
      { path: '/events', name: 'events', component: { template: '<div/>' } },
      { path: '/event-mode', name: 'event-mode', component: { template: '<div/>' } },
    ],
  })
  await router.push({ name: 'login' })
  await router.isReady()
  return mount(LoginView, {
    global: { plugins: [router] },
  })
}

describe('LoginView PIN keypad', () => {
  beforeEach(() => {
    resetStore()
    ensureShiftForSubject.mockClear()
    store.bundle.value = {
      organisation_id: 1,
      events: [waiterEvent()],
    } as never
    store.selectedEventId.value = 1
    store.waiter.value = null
  })

  it('enters PIN via on-screen keypad and requires Anmelden', async () => {
    const wrapper = await mountLogin()
    await nextTick()
    expect(wrapper.find('input').exists()).toBe(false)
    const keys = wrapper.findAll('button.key')
    expect(keys.length).toBeGreaterThanOrEqual(10)
    for (const d of ['1', '2', '3', '4']) {
      await keys.find((b) => b.text() === d)!.trigger('click')
    }
    expect(store.waiter.value).toBeNull()
    await wrapper.find('form.login-form').trigger('submit')
    await flushPromises()
    expect(store.waiter.value?.uuid).toBe('waiter-1')
    expect(ensureShiftForSubject).toHaveBeenCalled()
    wrapper.unmount()
  })

  it('shows error on wrong PIN and allows retry without logging in', async () => {
    const wrapper = await mountLogin()
    await nextTick()
    const keys = wrapper.findAll('button.key')
    for (const d of ['9', '9', '9', '9']) {
      await keys.find((b) => b.text() === d)!.trigger('click')
    }
    await wrapper.find('form.login-form').trigger('submit')
    await flushPromises()
    expect(store.waiter.value).toBeNull()
    expect(wrapper.text()).toContain('PIN ungültig')
    for (const d of ['1', '2', '3', '4']) {
      await keys.find((b) => b.text() === d)!.trigger('click')
    }
    await wrapper.find('form.login-form').trigger('submit')
    await flushPromises()
    expect(store.waiter.value?.name).toBe('Anna')
    wrapper.unmount()
  })
})
