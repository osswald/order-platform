import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import TaxCodes from './TaxCodes.vue'
import { vuetifyStubs } from '../../tests/helpers/vuetifyStub.js'

vi.mock('../api', () => ({
  apiFetch: vi.fn(),
  apiJson: vi.fn(),
}))

import { apiFetch, apiJson } from '../api'

const sampleCountries = [{ id: 3, code: 'CH', name: 'Schweiz' }]
const sampleTaxCodes = [
  {
    id: 1,
    country_id: 3,
    name: 'Normalsatz',
    country: sampleCountries[0],
    rates: [{ id: 1, rate_percent: 8.1, valid_from: '2024-01-01', valid_to: null }],
  },
]

async function mountTaxCodes(path = '/tax-codes', { isAdmin = false } = {}) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/tax-codes', name: 'tax-codes', component: TaxCodes },
      { path: '/tax-codes/new', name: 'tax-codes-new', component: TaxCodes },
      { path: '/tax-codes/:id(\\d+)', name: 'tax-codes-detail', component: TaxCodes },
    ],
  })
  await router.push(path)
  await router.isReady()

  const wrapper = mount(TaxCodes, {
    props: { isAdmin },
    global: {
      plugins: [router],
      stubs: {
        ...vuetifyStubs(),
        ListDetailLayout: {
          template: '<div :data-show-create="String(showCreate)"><slot name="detail" /><slot name="table" /></div>',
          props: ['showCreate'],
        },
        VqDataTable: { template: '<div data-testid="tax-codes-table" />' },
      },
    },
  })
  await flushPromises()
  return wrapper
}

describe('TaxCodes', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiJson.mockImplementation(async (path) => {
      if (path === '/countries/') return sampleCountries
      return sampleCountries
    })
    apiFetch.mockImplementation(async (path) => {
      if (path === '/tax-codes/') {
        return { ok: true, json: async () => sampleTaxCodes }
      }
      return { ok: true, json: async () => sampleTaxCodes[0] }
    })
  })

  it('renders tax code list', async () => {
    const wrapper = await mountTaxCodes('/tax-codes')
    expect(wrapper.find('[data-testid="tax-codes-table"]').exists()).toBe(true)
    expect(apiFetch).toHaveBeenCalledWith('/tax-codes/')
  })

  it('shows create affordance for platform admin only', async () => {
    const memberWrapper = await mountTaxCodes('/tax-codes', { isAdmin: false })
    const adminWrapper = await mountTaxCodes('/tax-codes', { isAdmin: true })
    expect(memberWrapper.find('[data-show-create]').attributes('data-show-create')).toBe('false')
    expect(adminWrapper.find('[data-show-create]').attributes('data-show-create')).toBe('true')
  })
})
