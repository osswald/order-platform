import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import KitchenMonitorHeader from './KitchenMonitorHeader.vue'
import KitchenProductList from './KitchenProductList.vue'
import type { KitchenProductSummary } from '@/utils/kitchenProductSummary'

function mountHeader(
  overrides: Partial<{
    stationLabel: string
    eventName: string
    viewMode: 'orders' | 'products'
    loading: boolean
    openOrderCount: number
  }> = {},
) {
  return mount(KitchenMonitorHeader, {
    props: {
      stationLabel: 'Grill',
      eventName: 'Fest',
      viewMode: 'orders',
      loading: false,
      openOrderCount: 8,
      ...overrides,
    },
  })
}

describe('KitchenMonitorHeader', () => {
  it('does not render a Zusätze checkbox', () => {
    const wrapper = mountHeader({ viewMode: 'products' })
    expect(wrapper.find('.extras-toggle').exists()).toBe(false)
    expect(wrapper.find('input[type="checkbox"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Produkte')
    expect(wrapper.text()).toContain('Bestellungen')
  })

  it('shows the open-ticket count next to the station label', () => {
    const wrapper = mountHeader({ openOrderCount: 8 })
    expect(wrapper.find('.kitchen-title strong').text()).toBe('Grill · 8 offen')
    expect(wrapper.find('.kitchen-event').text()).toBe('Fest')
  })

  it('shows 0 offen when the board is empty', () => {
    const wrapper = mountHeader({ openOrderCount: 0 })
    expect(wrapper.find('.kitchen-title strong').text()).toBe('Grill · 0 offen')
  })

  it('keeps the open-ticket count visible on Produkte', () => {
    const wrapper = mountHeader({ viewMode: 'products', openOrderCount: 3 })
    expect(wrapper.find('.kitchen-title strong').text()).toBe('Grill · 3 offen')
  })
})

describe('KitchenProductList', () => {
  it('always renders standalone addition cards without a showAdditions prop', () => {
    const summary: KitchenProductSummary = {
      articles: [
        {
          key: '10',
          articleId: 10,
          name: 'Burger',
          totalQty: 2,
          breakdown: [{ label: 'Tisch 4', qty: 2 }],
          color: null,
          sortKey: 0,
          additionLabels: ['2x Käse'],
          note: 'scharf',
        },
      ],
      additions: [
        {
          key: '30',
          articleId: 30,
          name: 'Salat',
          totalQty: 1,
          breakdown: [{ label: 'Tisch 4', qty: 1 }],
          color: null,
          sortKey: 1,
          additionLabels: [],
          note: '',
        },
      ],
    }

    const wrapper = mount(KitchenProductList, { props: { summary } })
    expect(wrapper.text()).toContain('Burger')
    expect(wrapper.text()).toContain('2x Käse')
    expect(wrapper.text()).not.toContain('+ 1x')
    expect(wrapper.text()).toContain('scharf')
    expect(wrapper.text()).toContain('Salat')
    expect(wrapper.findAll('.product-card')).toHaveLength(2)
    expect(wrapper.findAll('.product-card--addition')).toHaveLength(1)
  })
})
