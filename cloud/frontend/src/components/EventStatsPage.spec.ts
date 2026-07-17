import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import EventStatsPage from './EventStatsPage.vue'
import { vuetifyStubs } from '../../tests/helpers/vuetifyStub.js'

vi.mock('../api', () => ({
  apiJson: vi.fn(),
}))

vi.mock('vue-chartjs', () => ({
  Bar: { template: '<div data-testid="bar-chart" />' },
  Line: { template: '<div data-testid="line-chart" />' },
  Pie: { template: '<div data-testid="pie-chart" />' },
}))

import { apiJson } from '../api'

const sampleEvent = {
  id: 5,
  name: 'Sommerfest',
  status: 'prod',
  start: '2026-06-25T08:00:00+00:00',
  end: '2026-06-25T22:00:00+00:00',
  organisation_id: 1,
  payment_mode: 'pay_later',
  payment_types: ['cash'],
}

const sampleConfig = {
  stations: [{ article_ids: [10, 11], name: 'Bar', uuid: 'u1', sort_order: 0, printer_appliance_id: null, printer_rules: [] }],
}

const sampleStats = {
  currency: 'CHF',
  from: '2026-06-25T08:00:00+00:00',
  to: '2026-06-25T12:00:00+00:00',
  bucket_count: 24,
  totals: {
    distinct_orders_count: 3,
    line_cents: 1500,
    paid_cents: 1500,
    open_cents: 0,
    average_order_value_cents: 500,
  },
  revenue_timeline: {
    bucket_count: 24,
    buckets: [{ start: '2026-06-25T08:00:00+00:00', end: '2026-06-25T08:10:00+00:00', label: '10:00' }],
    line_cents: [1500],
  },
  top_articles: [{ article_id: 10, name: 'Bratwurst', qty: 5, line_cents: 1500 }],
  by_order_source: [
    { source: 'waiter', label: 'Kellner', qty: 5, line_cents: 1500 },
  ],
  article_timeline: { bucket_count: 24, buckets: [], series: [], totals: [] },
  category_timeline: { bucket_count: 24, buckets: [], series: [], totals: [] },
  by_payment_type: [{ type: 'cash', label: 'Cash', amount_cents: 1500 }],
  by_waiter: [{ name: 'Anna', order_count: 3, qty: 5, line_cents: 1500, paid_cents: 1500 }],
  by_station: [{ name: 'Bar', qty: 5, line_cents: 1500 }],
}

describe('EventStatsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(apiJson).mockImplementation(async (path: string) => {
      if (path.startsWith('/events/5/stats')) return sampleStats
      if (path.startsWith('/events/5/configuration')) return sampleConfig
      if (path === '/events/5') return sampleEvent
      if (path === '/articles/') {
        return [
          { id: 10, name: 'Bratwurst', article_category_id: 1, article_category_name: 'Food' },
          { id: 11, name: 'Bier', article_category_id: 2, article_category_name: 'Drinks' },
        ]
      }
      throw new Error(`unexpected path ${path}`)
    })
  })

  it('loads stats with timeframe query on mount', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/events/:id/stats', component: EventStatsPage }],
    })
    await router.push('/events/5/stats')
    await router.isReady()

    const wrapper = mount(EventStatsPage, {
      props: { activeOrganisationId: 1 },
      global: {
        plugins: [router],
        stubs: vuetifyStubs(),
      },
    })

    await flushPromises()

    const statsCall = vi.mocked(apiJson).mock.calls.find(([path]) => String(path).includes('/events/5/stats'))
    expect(statsCall).toBeTruthy()
    expect(String(statsCall?.[0])).toContain('from=')
    expect(String(statsCall?.[0])).toContain('to=')
    expect(wrapper.text()).toContain('Statistik')
  })
})
