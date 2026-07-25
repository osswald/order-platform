import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, nextTick } from 'vue'
import { mount, type VueWrapper } from '@vue/test-utils'
import { useKeyboardBottomInset } from './useKeyboardBottomInset'

type VvMock = {
  height: number
  offsetTop: number
  addEventListener: (type: string, fn: () => void) => void
  removeEventListener: (type: string, fn: () => void) => void
}

function mountInset() {
  let insetRef: ReturnType<typeof useKeyboardBottomInset> | null = null
  const Comp = defineComponent({
    setup() {
      insetRef = useKeyboardBottomInset()
      return { inset: insetRef }
    },
    template: '<div>{{ inset }}</div>',
  })
  const wrapper = mount(Comp)
  return {
    wrapper: wrapper as VueWrapper,
    get inset() {
      return insetRef!
    },
  }
}

describe('useKeyboardBottomInset', () => {
  const listeners = new Map<string, Set<() => void>>()
  let vv: VvMock
  let originalVv: VisualViewport | null | undefined
  let originalInnerHeight: number

  beforeEach(() => {
    listeners.clear()
    originalVv = window.visualViewport
    originalInnerHeight = window.innerHeight
    vv = {
      height: 800,
      offsetTop: 0,
      addEventListener: (type, fn) => {
        if (!listeners.has(type)) listeners.set(type, new Set())
        listeners.get(type)!.add(fn)
      },
      removeEventListener: (type, fn) => {
        listeners.get(type)?.delete(fn)
      },
    }
    Object.defineProperty(window, 'visualViewport', {
      configurable: true,
      value: vv,
    })
    Object.defineProperty(window, 'innerHeight', {
      configurable: true,
      value: 800,
    })
  })

  afterEach(() => {
    Object.defineProperty(window, 'visualViewport', {
      configurable: true,
      value: originalVv,
    })
    Object.defineProperty(window, 'innerHeight', {
      configurable: true,
      value: originalInnerHeight,
    })
  })

  it('reports 0 when visualViewport height matches the layout viewport', async () => {
    const { wrapper, inset } = mountInset()
    await nextTick()
    expect(inset.value).toBe(0)
    wrapper.unmount()
  })

  it('reports 0 when visualViewport is missing', async () => {
    Object.defineProperty(window, 'visualViewport', {
      configurable: true,
      value: undefined,
    })
    const { wrapper, inset } = mountInset()
    await nextTick()
    expect(inset.value).toBe(0)
    wrapper.unmount()
  })

  it('reports positive inset when the visual viewport shrinks', async () => {
    const { wrapper, inset } = mountInset()
    await nextTick()
    vv.height = 420
    vv.offsetTop = 0
    for (const fn of listeners.get('resize') || []) fn()
    await nextTick()
    expect(inset.value).toBe(380)
    wrapper.unmount()
  })

  it('accounts for visualViewport offsetTop', async () => {
    const { wrapper, inset } = mountInset()
    await nextTick()
    vv.height = 500
    vv.offsetTop = 50
    for (const fn of listeners.get('scroll') || []) fn()
    await nextTick()
    expect(inset.value).toBe(250)
    wrapper.unmount()
  })

  it('removes listeners on unmount', async () => {
    const { wrapper } = mountInset()
    await nextTick()
    expect(listeners.get('resize')?.size).toBe(1)
    wrapper.unmount()
    expect(listeners.get('resize')?.size).toBe(0)
  })
})
