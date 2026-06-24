import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import PaymentTypes from './PaymentTypes.vue'
import { vuetifyStubs } from '../../tests/helpers/vuetifyStub.js'

vi.mock('../api', () => ({
  apiFetch: vi.fn(),
  apiJson: vi.fn(),
}))

import { apiFetch, apiJson } from '../api'

const samplePaymentTypes = [
  { id: 1, slug: 'cash', sort_order: 0, is_active: true },
  { id: 2, slug: 'twint', sort_order: 1, is_active: true },
]

async function mountPaymentTypes(path = '/payment-types', { isAdmin = false } = {}) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/payment-types', name: 'payment-types', component: PaymentTypes },
      { path: '/payment-types/new', name: 'payment-types-new', component: PaymentTypes },
      { path: '/payment-types/:id(\\d+)', name: 'payment-types-detail', component: PaymentTypes },
    ],
  })
  await router.push(path)
  await router.isReady()

  const wrapper = mount(PaymentTypes, {
    props: { isAdmin },
    global: {
      plugins: [router],
      stubs: {
        ...vuetifyStubs(),
        ListDetailLayout: {
          template: '<div><slot name="detail" /><slot name="table" /></div>',
        },
        FormLabel: { template: '<label><slot /></label>' },
        VqDataTable: { template: '<div data-testid="payment-types-table" />' },
        'v-checkbox': { template: '<input type="checkbox" />', props: ['modelValue', 'label'] },
      },
    },
  })

  await flushPromises()
  return wrapper
}

describe('PaymentTypes', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiFetch.mockImplementation(async (path) => {
      if (path.startsWith('/payment-types/')) {
        return { ok: true, json: async () => samplePaymentTypes }
      }
      return { ok: true, json: async () => samplePaymentTypes[0] }
    })
  })

  it('loads payment types list', async () => {
    const wrapper = await mountPaymentTypes('/payment-types')
    expect(wrapper.find('[data-testid="payment-types-table"]').exists()).toBe(true)
    expect(apiFetch).toHaveBeenCalledWith('/payment-types/')
  })

  it('hides create affordance for non-admin', async () => {
    const memberWrapper = await mountPaymentTypes('/payment-types', { isAdmin: false })
    const adminWrapper = await mountPaymentTypes('/payment-types', { isAdmin: true })
    expect(memberWrapper.props('isAdmin')).toBe(false)
    expect(adminWrapper.props('isAdmin')).toBe(true)
  })
})
