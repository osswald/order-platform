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
  pickupPrefixMode: 'register',
}

function mountFields(formOverrides: Partial<EventStammdatenForm> = {}) {
  const form = { ...baseForm, ...formOverrides }
  return mount(EventStammdatenFields, {
    props: {
      form,
      'onUpdate:form': (value: EventStammdatenForm) => {
        Object.assign(form, value)
      },
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
        'v-select': {
          template:
            '<select data-testid="v-select" :disabled="disabled" :value="modelValue" @change="$emit(\'update:modelValue\', $event.target.value)"><option v-for="item in items" :key="item.value || item" :value="item.value ?? item">{{ item.title || item.label || item }}</option></select>',
          props: ['modelValue', 'items', 'itemTitle', 'itemValue', 'disabled', 'placeholder', 'multiple'],
        },
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

  it('shows pickup prefix mode select in Stammdaten', () => {
    const wrapper = mountFields()
    expect(wrapper.find('[data-testid="stammdaten-pickup-prefix-mode"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Abholcode-Buchstabe von')
  })

  it('updates pickupPrefixMode when Station is chosen', async () => {
    const form: EventStammdatenForm = { ...baseForm }
    const wrapper = mount(EventStammdatenFields, {
      props: {
        form,
        'onUpdate:form': (value: EventStammdatenForm) => {
          Object.assign(form, value)
        },
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
          'v-select': {
            template:
              '<select :data-testid="$attrs[\'data-testid\'] || \'v-select\'" :disabled="disabled" :value="modelValue" @change="$emit(\'update:modelValue\', $event.target.value)"><option v-for="item in items" :key="item.value || item" :value="item.value ?? item">{{ item.title || item.label || item }}</option></select>',
            props: ['modelValue', 'items', 'itemTitle', 'itemValue', 'disabled', 'placeholder', 'multiple'],
          },
        },
      },
    })
    const modeSelect = wrapper.find('[data-testid="stammdaten-pickup-prefix-mode"]')
    await modeSelect.setValue('station')
    expect(form.pickupPrefixMode).toBe('station')
  })

  it('disables pickup prefix mode outside config and shows lock hint', () => {
    const wrapper = mountFields({ status: 'prod', pickupPrefixMode: 'station' })
    const modeSelect = wrapper.find('[data-testid="stammdaten-pickup-prefix-mode"]')
    expect(modeSelect.attributes('disabled')).toBeDefined()
    expect(wrapper.find('[data-testid="stammdaten-pickup-prefix-mode-locked-hint"]').exists()).toBe(
      true,
    )
  })
})
