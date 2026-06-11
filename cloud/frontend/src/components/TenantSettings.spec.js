import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import TenantSettings from './TenantSettings.vue'
import { vuetifyStubs } from '../../tests/helpers/vuetifyStub.js'

vi.mock('../api', () => ({
  apiFetch: vi.fn(),
}))

import { apiFetch } from '../api'

function companyPayload(id, name) {
  return {
    id,
    name,
    address: `${name} street`,
    zip: '8000',
    city: 'Zurich',
    country: 'CH',
  }
}

describe('TenantSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('reloads form data when activeHireCompanyId changes', async () => {
    apiFetch.mockImplementation(async (path) => {
      if (path === '/hire-companies/1') {
        return { ok: true, json: async () => companyPayload(1, 'Tenant A') }
      }
      if (path === '/hire-companies/2') {
        return { ok: true, json: async () => companyPayload(2, 'Tenant B') }
      }
      return { ok: false, text: async () => 'not found' }
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

    expect(apiFetch).toHaveBeenCalledWith('/hire-companies/2')
    expect(wrapper.find('input').element.value).toBe('Tenant B')
  })
})
