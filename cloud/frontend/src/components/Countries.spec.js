import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import Countries from './Countries.vue'
import { vuetifyStubs } from '../../tests/helpers/vuetifyStub.js'

vi.mock('../api', () => ({
  apiFetch: vi.fn(),
}))

import { apiFetch } from '../api'

const sampleCountries = [
  { id: 1, code: 'DE', name: 'Deutschland' },
  { id: 3, code: 'CH', name: 'Schweiz' },
]

async function mountCountries(path = '/countries', { isAdmin = false } = {}) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/countries', name: 'countries', component: Countries },
      { path: '/countries/new', name: 'countries-new', component: Countries },
      { path: '/countries/:id(\\d+)', name: 'countries-detail', component: Countries },
    ],
  })
  await router.push(path)
  await router.isReady()

  const wrapper = mount(Countries, {
    props: { isAdmin },
    global: {
      plugins: [router],
      stubs: {
        ...vuetifyStubs(),
        ListDetailLayout: {
          template: '<div :data-show-create="String(showCreate)"><slot name="detail" /><slot name="table" /></div>',
          props: ['showCreate'],
        },
        VqDataTable: { template: '<div data-testid="countries-table" />' },
      },
    },
  })
  await flushPromises()
  return wrapper
}

describe('Countries', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiFetch.mockImplementation(async (path) => {
      if (path === '/countries/') {
        return { ok: true, json: async () => sampleCountries }
      }
      return { ok: true, json: async () => sampleCountries[0] }
    })
  })

  it('renders country list', async () => {
    const wrapper = await mountCountries('/countries')
    expect(wrapper.find('[data-testid="countries-table"]').exists()).toBe(true)
    expect(apiFetch).toHaveBeenCalledWith('/countries/')
  })

  it('shows create affordance for platform admin only', async () => {
    const memberWrapper = await mountCountries('/countries', { isAdmin: false })
    const adminWrapper = await mountCountries('/countries', { isAdmin: true })
    expect(memberWrapper.find('[data-show-create]').attributes('data-show-create')).toBe('false')
    expect(adminWrapper.find('[data-show-create]').attributes('data-show-create')).toBe('true')
  })
})
