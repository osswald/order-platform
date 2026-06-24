import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import EventBookkeepingTab from './EventBookkeepingTab.vue'
import { vuetifyStubs } from '../../tests/helpers/vuetifyStub.js'

vi.mock('../api', () => ({
  apiJson: vi.fn(),
}))

import { apiJson } from '../api'

const sampleReport = {
  event_id: 1,
  currency: 'CHF',
  configuration_ok: true,
  warnings: [],
  summary: [
    {
      debit_account: { number: '1000', name: 'Kasse' },
      credit_account: { number: '3400', name: 'Ertrag' },
      tax_code: { name: 'Normalsatz', rate_percent: 8.1 },
      net_cents: 46253,
      vat_cents: 3747,
      gross_cents: 50000,
      subsidiary_code: 'K01',
      subsidiary_name: 'Kasse Bar',
      collective_bill_name: null,
    },
  ],
  detail: [],
}

describe('EventBookkeepingTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiJson.mockResolvedValue(sampleReport)
  })

  it('loads bookkeeping report on mount', async () => {
    const wrapper = mount(EventBookkeepingTab, {
      props: { eventId: 42, currency: 'CHF' },
      global: {
        stubs: {
          ...vuetifyStubs(),
          VqDataTable: { template: '<div data-testid="bookkeeping-table" />' },
        },
      },
    })

    await flushPromises()

    expect(apiJson).toHaveBeenCalledWith('/events/42/bookkeeping?view=both')
    expect(wrapper.text()).toContain('Buchhaltung Zusammenfassung')
    expect(wrapper.find('[data-testid="bookkeeping-table"]').exists()).toBe(true)
  })
})
