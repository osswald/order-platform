import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import OrganisationLendingDialog from './OrganisationLendingDialog.vue'
import de from '../locales/de.json'
import { vuetifyStubs } from '../../tests/helpers/vuetifyStub.js'

vi.mock('../api', () => ({
  apiJson: vi.fn(),
}))

import { apiJson } from '../api'

const i18n = createI18n({ legacy: false, locale: 'de', messages: { de } })

const rental = {
  id: 7,
  hire_company_id: 1,
  organisation_id: 3,
  organisation_name: 'FC',
  start_date: '2026-06-12',
  end_date: '2026-06-15',
  label: null,
  display_name: 'FC',
  filled: false,
  lendings: [],
  zubehoer_lines: [],
}

describe('OrganisationLendingDialog rental choice', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(apiJson).mockImplementation(async (path: string, init?: RequestInit) => {
      if (path.startsWith('/rentals/?organisation_id=')) return [rental]
      if (path.startsWith('/appliances/?')) {
        return [{ id: 11, name: 'Pi-01', type: 'server', lendable: true }]
      }
      if (path === '/rentals/7/appliances' && init?.method === 'POST') return { ...rental, filled: true }
      if (path === '/rentals/' && init?.method === 'POST') return { ...rental, id: 99 }
      throw new Error(`unexpected ${init?.method || 'GET'} ${path}`)
    })
  })

  function mountDialog() {
    return mount(OrganisationLendingDialog, {
      props: {
        visible: true,
        organisationId: 3,
        organisationName: 'FC',
      },
      global: {
        plugins: [i18n],
        stubs: {
          ...vuetifyStubs(),
          FormLabel: { template: '<label><slot /></label>' },
          ApplianceTypeChip: { template: '<span />' },
          'v-dialog': { template: '<div><slot /></div>', props: ['modelValue'] },
          'v-card': { template: '<div><slot /></div>' },
          'v-card-title': { template: '<div><slot /></div>' },
          'v-card-text': { template: '<div><slot /></div>' },
          'v-card-actions': { template: '<div><slot /></div>' },
          'v-spacer': { template: '<div />' },
          'v-form': { template: '<form @submit.prevent="$emit(\'submit\')"><slot /></form>' },
          'v-btn-toggle': {
            props: ['modelValue'],
            emits: ['update:modelValue'],
            template:
              '<div data-testid="rental-mode-toggle"><slot /></div>',
          },
          'v-btn': {
            props: ['value', 'loading', 'disabled', 'color', 'variant'],
            emits: ['click'],
            template:
              '<button type="button" v-bind="$attrs" :data-value="value" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>',
          },
          'v-select': {
            props: ['modelValue', 'items', 'disabled', 'loading', 'multiple'],
            emits: ['update:modelValue'],
            inheritAttrs: false,
            template:
              '<select v-bind="$attrs" :disabled="disabled" @change="$emit(\'update:modelValue\', multiple ? [Number($event.target.value)] : Number($event.target.value))"><option v-for="item in items || []" :key="item.value" :value="item.value">{{ item.title }}</option></select>',
          },
          'v-text-field': { template: '<input />', props: ['modelValue'] },
          'v-menu': { template: '<div><slot /><slot name="activator" :props="{}" /></div>' },
          'v-date-picker': { template: '<div />' },
          'v-list-item': { template: '<div />' },
          'v-list-subheader': { template: '<div />' },
        },
      },
    })
  }

  it('assigns selected appliances to an existing rental', async () => {
    const wrapper = mountDialog()
    await flushPromises()
    expect(apiJson).toHaveBeenCalledWith('/rentals/?organisation_id=3')
    const vm = wrapper.vm as {
      selectedRentalId: number | null
      selectedIds: number[]
      submit: () => Promise<void>
    }
    vm.selectedRentalId = 7
    await flushPromises()
    vm.selectedIds = [11]
    await vm.submit()
    await flushPromises()
    expect(apiJson).toHaveBeenCalledWith(
      '/rentals/7/appliances',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ appliance_id: 11 }),
      }),
    )
  })

  it('creates a new rental when mode is create', async () => {
    const wrapper = mountDialog()
    await flushPromises()
    const vm = wrapper.vm as {
      rentalMode: string
      selectedIds: number[]
      submit: () => Promise<void>
    }
    vm.rentalMode = 'create'
    await flushPromises()
    vm.selectedIds = [11]
    await vm.submit()
    await flushPromises()
    const createCall = vi.mocked(apiJson).mock.calls.find(
      (call) => call[0] === '/rentals/' && call[1]?.method === 'POST',
    )
    expect(createCall).toBeTruthy()
    const body = JSON.parse(String(createCall![1]?.body))
    expect(body.organisation_id).toBe(3)
    expect(body.appliance_ids).toEqual([11])
  })
})
