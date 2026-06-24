import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import TenantSettings from './TenantSettings.vue'
import { vuetifyStubs } from '../../tests/helpers/vuetifyStub.js'

vi.mock('../api', () => ({
  apiJson: vi.fn(),
}))

import { apiJson } from '../api'

function companyPayload(id: number, name: string) {
  return {
    id,
    name,
    address: `${name} street`,
    zip: '8000',
    city: 'Zurich',
    country_id: 3,
    country: { id: 3, code: 'CH', name: 'Schweiz' },
  }
}

describe('TenantSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('reloads form data when activeHireCompanyId changes', async () => {
    vi.mocked(apiJson).mockImplementation(async (path: string) => {
      if (path === '/countries/') return [{ id: 3, code: 'CH', name: 'Schweiz' }]
      if (path === '/hire-companies/1') return companyPayload(1, 'Tenant A')
      if (path === '/hire-companies/2') return companyPayload(2, 'Tenant B')
      throw new Error('not found')
    })

    const wrapper = mount(TenantSettings, {
      props: { activeHireCompanyId: 1 },
      global: {
        stubs: {
          ...vuetifyStubs(),
          ReceiptPrintingSection: { template: '<div />' },
          FormLabel: { template: '<label><slot /></label>' },
        },
      },
    })

    await flushPromises()
    expect(wrapper.find('input').element.value).toBe('Tenant A')

    await wrapper.setProps({ activeHireCompanyId: 2 })
    await flushPromises()

    expect(apiJson).toHaveBeenCalledWith('/hire-companies/2')
    expect(wrapper.find('input').element.value).toBe('Tenant B')
  })
})
