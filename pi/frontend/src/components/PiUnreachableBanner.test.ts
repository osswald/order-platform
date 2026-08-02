import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { computed, ref } from 'vue'

const probeNow = vi.fn()
const status = ref<'unknown' | 'reachable' | 'unreachable'>('unreachable')
const probing = ref(false)
const unreachable = computed(() => status.value === 'unreachable')

vi.mock('@/composables/usePiConnectivity', () => ({
  usePiConnectivity: () => ({
    status,
    probing,
    unreachable,
    probeNow,
    ensureReachable: vi.fn(),
  }),
}))

import PiUnreachableBanner from './PiUnreachableBanner.vue'

describe('PiUnreachableBanner', () => {
  beforeEach(() => {
    probeNow.mockReset()
    probeNow.mockResolvedValue(true)
    status.value = 'unreachable'
    probing.value = false
  })

  function mountBanner() {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', name: 'hub', component: { template: '<div/>' } },
        { path: '/connection-setup', name: 'connection-setup', component: { template: '<div/>' } },
      ],
    })
    const push = vi.spyOn(router, 'push')
    const wrapper = mount(PiUnreachableBanner, {
      global: { plugins: [router] },
    })
    return { wrapper, router, push }
  }

  it('shows when Pi is unreachable', () => {
    const { wrapper } = mountBanner()
    expect(wrapper.text()).toContain('Keine Verbindung zur Kasse')
    expect(wrapper.text()).toContain('Erneut prüfen')
    expect(wrapper.text()).toContain('Verbindung ändern')
  })

  it('hides when Pi is reachable', async () => {
    status.value = 'reachable'
    const { wrapper } = mountBanner()
    expect(wrapper.find('.pi-unreachable-banner').exists()).toBe(false)
  })

  it('retry re-probes and hides after recovery', async () => {
    const { wrapper } = mountBanner()
    probeNow.mockImplementation(async () => {
      status.value = 'reachable'
      return true
    })
    await wrapper.get('button.btn.primary').trigger('click')
    await flushPromises()
    expect(probeNow).toHaveBeenCalled()
    expect(wrapper.find('.pi-unreachable-banner').exists()).toBe(false)
  })

  it('navigates to connection-setup without clearing session state itself', async () => {
    const { wrapper, push } = mountBanner()
    const changeBtn = wrapper.findAll('button').find((b) => b.text().includes('Verbindung ändern'))
    expect(changeBtn).toBeTruthy()
    await changeBtn!.trigger('click')
    expect(push).toHaveBeenCalledWith({ name: 'connection-setup' })
  })
})
