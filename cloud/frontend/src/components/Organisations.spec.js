import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import Organisations from './Organisations.vue'
import SectionNavLayout from './SectionNavLayout.vue'
import { vuetifyStubs } from '../../tests/helpers/vuetifyStub.js'

vi.mock('../api', () => ({
  apiFetch: vi.fn(),
}))

import { apiFetch } from '../api'

const sampleOrg = {
  id: 1,
  name: 'Vendiqo GmbH',
  address: 'Musterstraße 1',
  zip: '12345',
  city: 'Berlin',
  country_id: 1,
  country: { id: 1, code: 'DE', name: 'Deutschland' },
  currency: 'EUR',
  user_ids: [],
}

const sampleCountries = [
  { id: 1, code: 'DE', name: 'Deutschland' },
  { id: 3, code: 'CH', name: 'Schweiz' },
]

function createOrganisationsRouter(initialPath) {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/organisations', name: 'organisations', component: Organisations },
      { path: '/organisations/new', name: 'organisations-new', component: Organisations },
      { path: '/organisations/:id(\\d+)', name: 'organisations-detail', component: Organisations },
    ],
  })
}

async function mountOrganisations(path) {
  const router = createOrganisationsRouter(path)
  await router.push(path)
  await router.isReady()

  const wrapper = mount(Organisations, {
    global: {
      plugins: [router],
      stubs: {
        ...vuetifyStubs(),
        ListDetailLayout: {
          template: '<div><slot name="detail" /><slot name="table" /></div>',
        },
        UserPicker: { template: '<div data-testid="user-picker" />' },
        OrganisationStammdatenFields: {
          template: '<div data-testid="stammdaten-fields" />',
          props: ['form', 'countryOptions', 'currencyOptions'],
        },
        OrganisationStripeSection: { template: '<div data-testid="stripe-section" />' },
        ReceiptPrintingSection: { template: '<div data-testid="receipt-section" />' },
        OrganisationLendingDialog: { template: '<div />' },
        VqDataTable: { template: '<div data-testid="vq-data-table" />' },
        'v-icon': true,
        'v-select': {
          template: '<select />',
          props: ['modelValue', 'items', 'label'],
        },
      },
    },
  })

  await flushPromises()
  return wrapper
}

describe('Organisations', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiFetch.mockImplementation(async (path) => {
      if (path === '/countries/') {
        return { ok: true, json: async () => sampleCountries }
      }
      if (path === '/organisations/') {
        return { ok: true, json: async () => [sampleOrg] }
      }
      if (path === '/organisations/1/appliance-lendings') {
        return {
          ok: true,
          json: async () => ({ current: [], planned: [], past: [] }),
        }
      }
      return { ok: true, json: async () => sampleOrg }
    })
  })

  it('renders a flat Stammdaten form without SectionNavLayout on create route', async () => {
    const wrapper = await mountOrganisations('/organisations/new')

    expect(wrapper.findComponent(SectionNavLayout).exists()).toBe(false)
    expect(wrapper.find('[data-testid="stammdaten-fields"]').exists()).toBe(true)
  })

  it('renders SectionNavLayout with five tabs on edit route', async () => {
    const wrapper = await mountOrganisations('/organisations/1')
    const layout = wrapper.findComponent(SectionNavLayout)

    expect(layout.exists()).toBe(true)
    expect(layout.props('sections')).toHaveLength(5)
    expect(layout.props('sections').map((section) => section.title)).toEqual([
      'Stammdaten',
      'Geräte/Ausleihen',
      'Kartenzahlung (Stripe)',
      'Belegvorlagen',
      'Mehrwert-/Umsatzsteuer',
    ])
  })

  it('shows the MWST coming-soon placeholder when the MWST tab is active', async () => {
    const wrapper = await mountOrganisations('/organisations/1')
    const layout = wrapper.findComponent(SectionNavLayout)
    const mwstButton = layout.findAll('.section-nav-item').find((button) =>
      button.text().includes('Mehrwert-/Umsatzsteuer'),
    )

    await mwstButton.trigger('click')

    expect(wrapper.text()).toContain('Inhalt folgt.')
  })
})
