import { beforeEach, describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { nextTick } from 'vue'
import type { EdgeBundleEvent } from '@/types/api'
import { resetStore } from '@tests/helpers/resetStore'
import * as store from '@/store'
import RegisterSelectView from './RegisterSelectView.vue'

function registerEvent(): EdgeBundleEvent {
  return {
    id: 1,
    name: 'Sommerfest',
    currency: 'CHF',
    payment_mode: 'pay_later',
    payment_types: ['cash'],
    configuration: {
      cash_registers: [{ uuid: 'register-1', name: 'Kasse 1', pin: '4321' }],
    },
  } as EdgeBundleEvent
}

async function mountRegister() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'register-select', component: RegisterSelectView },
      {
        path: '/register/:registerUuid',
        name: 'register-hub',
        component: { template: '<div/>' },
      },
      { path: '/events', name: 'events', component: { template: '<div/>' } },
      { path: '/event-mode', name: 'event-mode', component: { template: '<div/>' } },
    ],
  })
  await router.push({ name: 'register-select' })
  await router.isReady()
  return mount(RegisterSelectView, {
    global: { plugins: [router] },
  })
}

describe('RegisterSelectView PIN keypad', () => {
  beforeEach(() => {
    resetStore()
    store.bundle.value = {
      organisation_id: 1,
      events: [registerEvent()],
    } as never
    store.selectedEventId.value = 1
    store.registerSession.value = null
  })

  it('enters PIN via on-screen keypad and requires Anmelden', async () => {
    const wrapper = await mountRegister()
    await nextTick()
    expect(wrapper.find('input').exists()).toBe(false)
    const keys = wrapper.findAll('button.key')
    for (const d of ['4', '3', '2', '1']) {
      await keys.find((b) => b.text() === d)!.trigger('click')
    }
    expect(store.registerSession.value).toBeNull()
    await wrapper.find('form.login-form').trigger('submit')
    await flushPromises()
    expect(store.registerSession.value?.uuid).toBe('register-1')
    wrapper.unmount()
  })

  it('shows error on wrong PIN and allows retry', async () => {
    const wrapper = await mountRegister()
    await nextTick()
    const keys = wrapper.findAll('button.key')
    for (const d of ['0', '0', '0', '0']) {
      await keys.find((b) => b.text() === d)!.trigger('click')
    }
    await wrapper.find('form.login-form').trigger('submit')
    await flushPromises()
    expect(store.registerSession.value).toBeNull()
    expect(wrapper.text()).toContain('PIN ungültig')
    for (const d of ['4', '3', '2', '1']) {
      await keys.find((b) => b.text() === d)!.trigger('click')
    }
    await wrapper.find('form.login-form').trigger('submit')
    await flushPromises()
    expect(store.registerSession.value?.name).toBe('Kasse 1')
    wrapper.unmount()
  })
})
