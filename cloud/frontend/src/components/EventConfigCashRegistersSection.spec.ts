import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import EventConfigCashRegistersSection from './EventConfigCashRegistersSection.vue'
import type { EventCashRegisterLocal } from '@/types/ui'
import { vuetifyStubs } from '../../tests/helpers/vuetifyStub.js'

function mountSection(cashRegisters: EventCashRegisterLocal[]) {
  return mount(EventConfigCashRegistersSection, {
    props: {
      modelValue: cashRegisters,
      'onUpdate:modelValue': (value: EventCashRegisterLocal[]) => {
        cashRegisters.splice(0, cashRegisters.length, ...value)
      },
      printerOptions: [{ id: 1, name: 'Kassen-Drucker' }],
    },
    global: {
      stubs: {
        ...vuetifyStubs(),
        FormLabel: { template: '<label><slot /></label>' },
      },
    },
  })
}

describe('EventConfigCashRegistersSection', () => {
  it('shows cash drawer options when a receipt printer is selected', () => {
    const registers: EventCashRegisterLocal[] = [
      {
        name: 'Hauptkasse',
        pickup_code_prefix: 'A',
        pin: '0000',
        layout_uuid: 'layout-1',
        receipt_printer_appliance_id: 1,
        cash_drawer_command: 'escp_pin2',
      },
    ]
    const wrapper = mountSection(registers)
    expect(wrapper.text()).toContain('Kassenschublade')
  })

  it('hides cash drawer field without receipt printer', () => {
    const registers: EventCashRegisterLocal[] = [
      {
        name: 'Hauptkasse',
        pickup_code_prefix: 'A',
        pin: '0000',
        layout_uuid: 'layout-1',
        receipt_printer_appliance_id: null,
        cash_drawer_command: 'none',
      },
    ]
    const wrapper = mountSection(registers)
    expect(wrapper.text()).not.toContain('Kassenschublade')
  })
})
