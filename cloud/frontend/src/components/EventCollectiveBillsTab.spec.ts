import { describe, expect, it, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import EventCollectiveBillsTab from './EventCollectiveBillsTab.vue'
import { vuetifyStubs } from '../../tests/helpers/vuetifyStub.js'

vi.mock('../api', () => ({
  apiJson: vi.fn(),
  apiFetch: vi.fn(),
}))

import { apiFetch, apiJson } from '../api'

const sampleList = {
  currency: 'CHF',
  country_code: 'CH',
  collective_bills: [
    {
      uuid: 'bill-uuid-1',
      name: 'Tisch 1',
      status: 'open',
      order_count: 2,
      line_cents: 5000,
      open_cents: 5000,
      paid_cents: 0,
      line_groups: [],
      created_at: '2026-07-01T10:00:00Z',
      closed_at: null,
    },
  ],
}

function mountTab() {
  return mount(EventCollectiveBillsTab, {
    props: { eventId: 7 },
    global: {
      stubs: {
        ...vuetifyStubs(),
        VqDataTable: { template: '<div data-testid="positions-table" />' },
        'v-expansion-panels': { template: '<div class="v-expansion-panels"><slot /></div>' },
        'v-expansion-panel': { template: '<div class="v-expansion-panel"><slot /></div>' },
        'v-expansion-panel-title': { template: '<div class="v-expansion-panel-title"><slot /></div>' },
        'v-expansion-panel-text': { template: '<div class="v-expansion-panel-text"><slot /></div>' },
        'v-chip': { template: '<span class="v-chip"><slot /></span>' },
        'v-checkbox': {
          template:
            '<label class="v-checkbox"><input type="checkbox" :checked="modelValue" @change="$emit(\'update:modelValue\', $event.target.checked)" /><slot /></label>',
          props: ['modelValue', 'label', 'density', 'hideDetails'],
          emits: ['update:modelValue'],
        },
        'v-dialog': {
          template: '<div v-if="modelValue" class="v-dialog" data-testid="pdf-settings-dialog"><slot /></div>',
          props: ['modelValue', 'maxWidth'],
        },
        'v-card': { template: '<div class="v-card"><slot /></div>' },
        'v-card-title': { template: '<div class="v-card-title"><slot /></div>' },
        'v-card-text': { template: '<div class="v-card-text"><slot /></div>' },
        'v-card-actions': { template: '<div class="v-card-actions"><slot /></div>' },
        'v-spacer': { template: '<span />' },
      },
    },
  })
}

describe('EventCollectiveBillsTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(apiJson).mockResolvedValue(sampleList)
    vi.mocked(apiFetch).mockResolvedValue({
      ok: true,
      blob: () => Promise.resolve(new Blob(['pdf'])),
    } as Response)
  })

  it('opens PDF settings dialog when download is clicked', async () => {
    const wrapper = mountTab()
    await flushPromises()

    expect(wrapper.find('[data-testid="pdf-settings-dialog"]').exists()).toBe(false)

    await wrapper.find('[data-testid="open-pdf-settings"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="pdf-settings-dialog"]').exists()).toBe(true)
    expect(apiFetch).not.toHaveBeenCalled()
  })

  it('downloads PDF with include_order_detail after confirming settings', async () => {
    const wrapper = mountTab()
    await flushPromises()

    await wrapper.find('[data-testid="open-pdf-settings"]').trigger('click')
    await flushPromises()

    await wrapper.find('.v-checkbox input').setValue(true)
    await wrapper.find('[data-testid="confirm-pdf-download"]').trigger('click')
    await flushPromises()

    expect(apiFetch).toHaveBeenCalledWith(
      '/events/7/collective-bills/bill-uuid-1/pdf?include_order_detail=true',
      expect.objectContaining({
        headers: expect.objectContaining({ 'Accept-Language': 'de' }),
      }),
    )
    expect(wrapper.find('[data-testid="pdf-settings-dialog"]').exists()).toBe(false)
  })
})
