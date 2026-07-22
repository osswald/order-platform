import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'

const replace = vi.fn()
const probeApiBase = vi.fn()
const setApiBase = vi.fn()
const getApiBase = vi.fn(() => 'http://192.168.192.10')

vi.mock('@/api', () => ({
  getApiBase: () => getApiBase(),
  setApiBase: (url: string) => setApiBase(url),
}))

vi.mock('@/utils/probeApiBase', () => ({
  PLAY_REVIEW_DEMO_API_BASE: 'https://play-review.demo.vendiqo.ch',
  probeApiBase: (...args: unknown[]) => probeApiBase(...args),
}))

import ConnectionSetupView from './ConnectionSetupView.vue'

function mountView() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/connection-setup', name: 'connection-setup', component: ConnectionSetupView },
      { path: '/events', name: 'events', component: { template: '<div/>' } },
    ],
  })
  router.replace = replace
  return mount(ConnectionSetupView, { global: { plugins: [router] } })
}

describe('ConnectionSetupView', () => {
  beforeEach(() => {
    replace.mockReset()
    probeApiBase.mockReset()
    setApiBase.mockReset()
    getApiBase.mockReturnValue('http://192.168.192.10')
    probeApiBase.mockResolvedValue({ reachable: true })
  })

  it('prefills current api base', async () => {
    const wrapper = mountView()
    await flushPromises()
    const input = wrapper.get('input[inputmode="url"]')
    expect((input.element as HTMLInputElement).value).toBe('http://192.168.192.10')
  })

  it('sets play review demo url, saves, and continues when Demo succeeds', async () => {
    const wrapper = mountView()
    await flushPromises()
    const demoBtn = wrapper.get('button.demo-btn')
    expect(demoBtn.text()).toBe('Demo')
    await demoBtn.trigger('click')
    await flushPromises()
    expect(probeApiBase).toHaveBeenCalledWith('https://play-review.demo.vendiqo.ch')
    const input = wrapper.get('input[inputmode="url"]')
    expect((input.element as HTMLInputElement).value).toBe('https://play-review.demo.vendiqo.ch')
    expect(setApiBase).toHaveBeenCalledWith('https://play-review.demo.vendiqo.ch')
    expect(replace).toHaveBeenCalledWith({ name: 'events' })
  })

  it('does not save when Demo probe fails', async () => {
    probeApiBase.mockResolvedValue({ reachable: false, reason: 'network' })
    const wrapper = mountView()
    await flushPromises()
    await wrapper.get('button.demo-btn').trigger('click')
    await flushPromises()
    expect(setApiBase).not.toHaveBeenCalled()
    expect(replace).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Pi nicht erreichbar')
  })

  it('saves api base after successful test', async () => {
    const wrapper = mountView()
    await flushPromises()
    await wrapper.get('button[type="button"].btn').trigger('click')
    await flushPromises()
    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()
    expect(setApiBase).toHaveBeenCalledWith('http://192.168.192.10')
    expect(replace).toHaveBeenCalledWith({ name: 'events' })
  })
})
