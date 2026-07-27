import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import KitchenMonitorHeader from './KitchenMonitorHeader.vue'
import KitchenProductList from './KitchenProductList.vue'
import type { KitchenProductSummary } from '@/utils/kitchenProductSummary'

describe('KitchenMonitorHeader', () => {
  it('does not render a Zusätze checkbox', () => {
    const wrapper = mount(KitchenMonitorHeader, {
      props: {
        stationLabel: 'Grill',
        eventName: 'Fest',
        viewMode: 'products',
        loading: false,
      },
    })
    expect(wrapper.find('.extras-toggle').exists()).toBe(false)
    expect(wrapper.find('input[type="checkbox"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Produkte')
    expect(wrapper.text()).toContain('Bestellungen')
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
          additionLabels: ['+ 1x 2x Käse'],
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
    expect(wrapper.text()).toContain('+ 1x 2x Käse')
    expect(wrapper.text()).toContain('scharf')
    expect(wrapper.text()).toContain('Salat')
    expect(wrapper.findAll('.product-card')).toHaveLength(2)
    expect(wrapper.findAll('.product-card--addition')).toHaveLength(1)
  })
})
