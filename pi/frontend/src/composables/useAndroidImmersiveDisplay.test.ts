import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { setAndroidImmersiveMode, useAndroidImmersiveDisplay } from './useAndroidImmersiveDisplay'

vi.mock('@/api', () => ({
  isAndroidApp: vi.fn(() => true),
}))

import { isAndroidApp } from '@/api'

describe('setAndroidImmersiveMode', () => {
  beforeEach(() => {
    vi.mocked(isAndroidApp).mockReturnValue(true)
    delete window.AndroidApp
  })

  it('is a no-op when not Android', () => {
    vi.mocked(isAndroidApp).mockReturnValue(false)
    const setImmersiveMode = vi.fn()
    window.AndroidApp = { setImmersiveMode }
    setAndroidImmersiveMode(true)
    expect(setImmersiveMode).not.toHaveBeenCalled()
  })

  it('is a no-op when bridge method is missing', () => {
    window.AndroidApp = { getAppInfo: () => '{}' }
    expect(() => setAndroidImmersiveMode(true)).not.toThrow()
  })

  it('calls AndroidApp.setImmersiveMode when present', () => {
    const setImmersiveMode = vi.fn()
    window.AndroidApp = { setImmersiveMode }
    setAndroidImmersiveMode(true)
    expect(setImmersiveMode).toHaveBeenCalledWith(true)
    setAndroidImmersiveMode(false)
    expect(setImmersiveMode).toHaveBeenCalledWith(false)
  })
})

describe('useAndroidImmersiveDisplay', () => {
  beforeEach(() => {
    vi.mocked(isAndroidApp).mockReturnValue(true)
    delete window.AndroidApp
  })

  it('enables immersive when route meta.immersive is true and disables on leave', async () => {
    const setImmersiveMode = vi.fn()
    window.AndroidApp = { setImmersiveMode }

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        {
          path: '/kitchen/:slug',
          name: 'kitchen',
          component: { template: '<div/>' },
          meta: { immersive: true },
        },
        {
          path: '/hub',
          name: 'hub',
          component: { template: '<div/>' },
          meta: {},
        },
      ],
    })
    await router.push('/kitchen/grill')

    const Host = defineComponent({
      setup() {
        useAndroidImmersiveDisplay()
        return () => null
      },
    })
    const wrapper = mount(Host, {
      global: { plugins: [router] },
    })
    await nextTick()
    expect(setImmersiveMode).toHaveBeenCalledWith(true)

    await router.push('/hub')
    await nextTick()
    expect(setImmersiveMode).toHaveBeenCalledWith(false)

    wrapper.unmount()
  })

  it('does not watch when not Android', async () => {
    vi.mocked(isAndroidApp).mockReturnValue(false)
    const setImmersiveMode = vi.fn()
    window.AndroidApp = { setImmersiveMode }

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        {
          path: '/',
          name: 'kitchen',
          component: { template: '<div/>' },
          meta: { immersive: true },
        },
      ],
    })
    await router.push('/')

    const Host = defineComponent({
      setup() {
        useAndroidImmersiveDisplay()
        return () => null
      },
    })
    mount(Host, { global: { plugins: [router] } })
    await nextTick()
    expect(setImmersiveMode).not.toHaveBeenCalled()
  })
})
