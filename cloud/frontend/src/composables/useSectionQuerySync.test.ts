import { describe, expect, it, vi } from 'vitest'
import { defineComponent, nextTick, ref } from 'vue'
import type { Ref } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { useSectionQuerySync } from './useSectionQuerySync'

const sections = [
  { id: 'stammdaten' },
  { id: 'stripe' },
  { id: 'buchhaltung' },
]

async function mountSync(options: {
  path: string
  activeTab?: string
  sectionList?: { id: string }[]
  enabled?: Ref<boolean> | boolean
}) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/detail/:id', name: 'detail', component: { template: '<div />' } }],
  })
  await router.push(options.path)
  await router.isReady()

  const activeTab = ref(options.activeTab ?? 'stammdaten')
  const sectionList = ref(options.sectionList ?? sections)
  const enabled =
    typeof options.enabled === 'boolean' || options.enabled === undefined
      ? ref(options.enabled ?? true)
      : options.enabled

  mount(
    defineComponent({
      setup() {
        useSectionQuerySync(activeTab, sectionList, { enabled })
        return () => null
      },
    }),
    { global: { plugins: [router] } },
  )

  await flushPromises()
  return { router, activeTab, sectionList, enabled }
}

describe('useSectionQuerySync', () => {
  it('applies a valid section query to the active tab', async () => {
    const { activeTab } = await mountSync({ path: '/detail/1?section=stripe' })
    expect(activeTab.value).toBe('stripe')
  })

  it('ignores unknown section ids in the query', async () => {
    const { activeTab, router } = await mountSync({ path: '/detail/1?section=missing' })
    expect(activeTab.value).toBe('stammdaten')
    expect(router.currentRoute.value.query.section).toBe('stammdaten')
  })

  it('writes section to the query when the active tab changes', async () => {
    const { activeTab, router } = await mountSync({ path: '/detail/1' })
    expect(router.currentRoute.value.query.section).toBe('stammdaten')

    activeTab.value = 'buchhaltung'
    await flushPromises()

    expect(router.currentRoute.value.query.section).toBe('buchhaltung')
  })

  it('does not replace when the query already matches the active tab', async () => {
    const { router, activeTab } = await mountSync({ path: '/detail/1?section=stripe' })
    expect(activeTab.value).toBe('stripe')

    const replaceSpy = vi.spyOn(router, 'replace')
    activeTab.value = 'stripe'
    await nextTick()
    await flushPromises()

    expect(replaceSpy).not.toHaveBeenCalled()
    replaceSpy.mockRestore()
  })

  it('does not write when enabled is false', async () => {
    const enabled = ref(false)
    const { activeTab, router } = await mountSync({
      path: '/detail/1',
      enabled,
    })

    expect(router.currentRoute.value.query.section).toBeUndefined()

    activeTab.value = 'stripe'
    await flushPromises()

    expect(router.currentRoute.value.query.section).toBeUndefined()
  })

  it('updates the query when the active tab falls back after sections change', async () => {
    const { activeTab, sectionList, router } = await mountSync({
      path: '/detail/1?section=stripe',
    })
    expect(activeTab.value).toBe('stripe')

    activeTab.value = 'stammdaten'
    await flushPromises()
    expect(router.currentRoute.value.query.section).toBe('stammdaten')

    // Simulate parent fallback when current tab is no longer available
    sectionList.value = [{ id: 'stationen' }, { id: 'layouts' }]
    activeTab.value = 'stationen'
    await flushPromises()

    expect(router.currentRoute.value.query.section).toBe('stationen')
  })

  it('preserves other query params when writing section', async () => {
    const { activeTab, router } = await mountSync({ path: '/detail/1?foo=bar' })
    expect(router.currentRoute.value.query).toMatchObject({ foo: 'bar', section: 'stammdaten' })

    activeTab.value = 'stripe'
    await flushPromises()

    expect(router.currentRoute.value.query).toMatchObject({ foo: 'bar', section: 'stripe' })
  })

  it('applies section from query when enabled becomes true', async () => {
    const enabled = ref(false)
    const { activeTab, router } = await mountSync({
      path: '/detail/1?section=buchhaltung',
      enabled,
    })
    expect(activeTab.value).toBe('stammdaten')

    enabled.value = true
    await flushPromises()

    expect(activeTab.value).toBe('buchhaltung')
    expect(router.currentRoute.value.query.section).toBe('buchhaltung')
  })
})
