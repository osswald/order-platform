import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import EventConfigCashRegistersSection from './EventConfigCashRegistersSection.vue'
import type { EventCashRegisterLocal } from '@/types/ui'
import { vuetifyStubs } from '../../tests/helpers/vuetifyStub.js'

const register: EventCashRegisterLocal = {
  name: 'Hauptkasse',
  pickup_code_prefix: 'A',
  pin: '0000',
  layout_uuid: 'layout-1',
  receipt_printer_appliance_id: null,
  cash_drawer_command: 'none',
}

function mountSection(props: { pickupPrefixMode?: 'register' | 'station' }) {
  const registers = [{ ...register }]
  return mount(EventConfigCashRegistersSection, {
    props: {
      modelValue: registers,
      'onUpdate:modelValue': (value: EventCashRegisterLocal[]) => {
        registers.splice(0, registers.length, ...value)
      },
      pickupPrefixMode: props.pickupPrefixMode ?? 'register',
      printerOptions: [{ id: 1, name: 'Kassen-Drucker' }],
    },
    global: {
      stubs: {
        ...vuetifyStubs(),
        FormLabel: { template: '<label><slot /></label>' },
        'v-select': {
          template:
            '<select data-testid="v-select" :disabled="disabled" :value="modelValue" @change="$emit(\'update:modelValue\', $event.target.value)"><option v-for="item in items" :key="item.value" :value="item.value">{{ item.title || item.label }}</option></select>',
          props: ['modelValue', 'items', 'itemTitle', 'itemValue', 'disabled', 'placeholder'],
        },
      },
    },
  })
}

describe('EventConfigCashRegistersSection pickup prefix mode', () => {
  it('does not show mode select (owned by Stammdaten)', () => {
    const wrapper = mountSection({ pickupPrefixMode: 'register' })
    expect(wrapper.find('[data-testid="pickup-prefix-mode"]').exists()).toBe(false)
  })

  it('shows register pickup prefix fields in register mode', () => {
    const wrapper = mountSection({ pickupPrefixMode: 'register' })
    expect(wrapper.find('[data-testid="register-pickup-prefix"]').exists()).toBe(true)
  })

  it('hides register pickup prefix fields in station mode', () => {
    const wrapper = mountSection({ pickupPrefixMode: 'station' })
    expect(wrapper.find('[data-testid="register-pickup-prefix"]').exists()).toBe(false)
  })
})
