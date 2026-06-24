import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import EventConfigStationsSection from './EventConfigStationsSection.vue'
import EventConfigKitchenMonitorsSection from './EventConfigKitchenMonitorsSection.vue'
import EventConfigWaitersSection from './EventConfigWaitersSection.vue'
import { vuetifyStubs } from '../../tests/helpers/vuetifyStub.js'

const globalMount = {
  global: {
    stubs: {
      ...vuetifyStubs(),
      FormLabel: { template: '<label><slot /></label>' },
      VqDataTable: {
        template: '<div data-testid="waiters-table"><slot name="item.name" :index="0" /><slot name="item.actions" :index="0" /></div>',
        props: ['items', 'headers', 'itemValue'],
      },
      'v-select': { template: '<select />', props: ['modelValue', 'items'] },
      'v-btn': {
        template: '<button type="button" @click="$emit(\'click\')"><slot /></button>',
        props: ['icon', 'variant', 'color', 'disabled'],
      },
    },
  },
}

describe('EventConfigStationsSection', () => {
  it('shows catalog loading hint', () => {
    const wrapper = mount(EventConfigStationsSection, {
      props: {
        modelValue: [],
        catalogLoading: true,
        catalogError: '',
        printerOptions: [],
        articleOptions: [],
        alternativePrintersEnabled: false,
      },
      ...globalMount,
    })
    expect(wrapper.text()).toContain('Artikel und Kellner werden geladen')
  })

  it('adds a station when add button is clicked', async () => {
    const stations = []
    const wrapper = mount(EventConfigStationsSection, {
      props: {
        modelValue: stations,
        'onUpdate:modelValue': (v) => {
          stations.splice(0, stations.length, ...v)
        },
        catalogLoading: false,
        catalogError: '',
        printerOptions: [],
        articleOptions: [],
        alternativePrintersEnabled: false,
      },
      ...globalMount,
    })
    await wrapper.find('.section-toolbar button').trigger('click')
    expect(stations).toHaveLength(1)
    expect(stations[0].article_ids).toEqual([])
  })
})

describe('EventConfigKitchenMonitorsSection', () => {
  it('adds a kitchen monitor row', async () => {
    const rows = []
    const wrapper = mount(EventConfigKitchenMonitorsSection, {
      props: {
        modelValue: rows,
        'onUpdate:modelValue': (v) => {
          rows.splice(0, rows.length, ...v)
        },
        printerOptions: [{ id: 7, name: 'Kitchen printer' }],
        kitchenMonitorPrinterOptions: [{ id: 7, name: 'Kitchen printer' }],
      },
      ...globalMount,
    })
    await wrapper.find('.section-toolbar button').trigger('click')
    expect(rows).toHaveLength(1)
    expect(rows[0].printer_appliance_id).toBe(7)
  })
})

describe('EventConfigWaitersSection', () => {
  it('emits import-from-org when import button is clicked', async () => {
    const wrapper = mount(EventConfigWaitersSection, {
      props: {
        modelValue: [{ _key: 'w-1', name: 'Anna', pin: '1234' }],
        catalogLoading: false,
        accountsEnabled: false,
      },
      ...globalMount,
    })
    const buttons = wrapper.findAll('.section-toolbar button')
    await buttons[1].trigger('click')
    expect(wrapper.emitted('import-from-org')).toHaveLength(1)
  })
})
