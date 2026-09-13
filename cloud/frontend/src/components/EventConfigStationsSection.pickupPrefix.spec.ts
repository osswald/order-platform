import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import EventConfigStationsSection from './EventConfigStationsSection.vue'
import type { EventStationLocal } from '@/types/ui'
import { vuetifyStubs } from '../../tests/helpers/vuetifyStub.js'

const station: EventStationLocal = {
  name: 'Grill',
  printer_appliance_id: null,
  printer_rules: [],
  article_ids: [],
  pickup_code_prefix: 'G',
}

function mountSection(props: {
  pickupPrefixMode?: 'register' | 'station'
  pickupPrefixModeLocked?: boolean
}) {
  const stations = [{ ...station }]
  return mount(EventConfigStationsSection, {
    props: {
      modelValue: stations,
      'onUpdate:modelValue': (value: EventStationLocal[]) => {
        stations.splice(0, stations.length, ...value)
      },
      pickupPrefixMode: props.pickupPrefixMode ?? 'register',
      pickupPrefixModeLocked: props.pickupPrefixModeLocked ?? false,
      catalogLoading: false,
      catalogError: '',
      printerOptions: [],
      articles: [],
      alternativePrintersEnabled: false,
    },
    global: {
      stubs: {
        ...vuetifyStubs(),
        FormLabel: { template: '<label><slot /></label>' },
        StationArticleTransferPicker: {
          template: '<div data-testid="article-transfer-picker" />',
          props: ['modelValue', 'articles', 'loading', 'disabled'],
        },
        'v-select': {
          template:
            '<select data-testid="v-select" :disabled="disabled" :value="modelValue" @change="$emit(\'update:modelValue\', $event.target.value)"><option v-for="item in items" :key="item.value" :value="item.value">{{ item.title || item.label }}</option></select>',
          props: ['modelValue', 'items', 'itemTitle', 'itemValue', 'disabled', 'placeholder'],
        },
      },
    },
  })
}

describe('EventConfigStationsSection pickup prefix mode', () => {
  it('hides station pickup prefix fields in register mode', () => {
    const wrapper = mountSection({ pickupPrefixMode: 'register' })
    expect(wrapper.find('[data-testid="station-pickup-prefix"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="pickup-prefix-mode"]').exists()).toBe(true)
  })

  it('shows station pickup prefix fields in station mode', () => {
    const wrapper = mountSection({ pickupPrefixMode: 'station' })
    expect(wrapper.find('[data-testid="station-pickup-prefix"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="pickup-prefix-mode"]').exists()).toBe(true)
  })

  it('disables mode control outside config and shows lock hint', () => {
    const wrapper = mountSection({
      pickupPrefixMode: 'station',
      pickupPrefixModeLocked: true,
    })
    const modeSelect = wrapper.find('[data-testid="pickup-prefix-mode"]')
    expect(modeSelect.attributes('disabled')).toBeDefined()
    expect(wrapper.find('[data-testid="pickup-prefix-mode-locked-hint"]').exists()).toBe(true)
  })

  it('initializes pickup_code_prefix when adding a station', async () => {
    const stations: EventStationLocal[] = []
    const wrapper = mount(EventConfigStationsSection, {
      props: {
        modelValue: stations,
        'onUpdate:modelValue': (value: EventStationLocal[]) => {
          stations.splice(0, stations.length, ...value)
        },
        pickupPrefixMode: 'station',
        catalogLoading: false,
        catalogError: '',
        printerOptions: [],
        articles: [],
        alternativePrintersEnabled: false,
      },
      global: {
        stubs: {
          ...vuetifyStubs(),
          FormLabel: { template: '<label><slot /></label>' },
          StationArticleTransferPicker: { template: '<div />' },
          'v-select': { template: '<select />', props: ['modelValue', 'items'] },
        },
      },
    })
    await wrapper.find('.section-toolbar button').trigger('click')
    expect(stations).toHaveLength(1)
    expect(stations[0].pickup_code_prefix).toBe('')
  })
})
