import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import EventStammdatenFields from './EventStammdatenFields.vue'
import type { EventStammdatenForm } from '@/types/ui'
import { vuetifyStubs } from '../../tests/helpers/vuetifyStub.js'

const baseForm: EventStammdatenForm = {
  name: 'Test Event',
  status: 'config',
  start: new Date('2026-06-01T10:00:00'),
  end: new Date('2026-06-01T22:00:00'),
  paymentMode: 'pay_later',
  paymentTypes: ['cash'],
  instantCollectiveBillName: '',
  offerPaymentReceipt: false,
  bluetoothPrintingEnabled: false,
  cashRegistersEnabled: false,
  shiftSettlementEnabled: false,
  vouchersEnabled: false,
  alternativePrintersEnabled: false,
  kitchenMonitorsEnabled: false,
  discountsEnabled: false,
}

function mountFields(formOverrides: Partial<EventStammdatenForm> = {}) {
  return mount(EventStammdatenFields, {
    props: {
      form: { ...baseForm, ...formOverrides },
      paymentModeOptions: [
        { label: 'Sofort', value: 'instant' },
        { label: 'Später', value: 'pay_later' },
      ],
      paymentTypeOptions: [{ label: 'Bar', value: 'cash' }],
    },
    global: {
      stubs: {
        ...vuetifyStubs(),
        FormLabel: { template: '<label><slot /></label>' },
        TwintQrField: { template: '<div />' },
        'v-switch': { template: '<input type="checkbox" />', props: ['modelValue'] },
      },
    },
  })
}

describe('EventStammdatenFields', () => {
  it('shows Sammelrechnung field when payment mode is instant', () => {
    const wrapper = mountFields({ paymentMode: 'instant' })
    expect(wrapper.text()).toContain('Sammelrechnung')
  })

  it('hides payment types when payment mode is instant', () => {
    const wrapper = mountFields({ paymentMode: 'instant' })
    expect(wrapper.text()).not.toContain('Zahlungsarten')
  })

  it('shows Bluetooth printing toggle next to payment receipt offer', () => {
    const wrapper = mountFields()
    expect(wrapper.text()).toContain('Bluetooth-Druck aktivieren')
    expect(wrapper.text()).toContain('Zahlungsbeleg nach Bezahlung anbieten')
  })
})
