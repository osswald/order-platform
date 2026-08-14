import { describe, expect, it, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import SumupReaderTelemetryTooltip from './SumupReaderTelemetryTooltip.vue'
import en from '../locales/en.json'
import { fetchSumupReaderTelemetry, type SumupReader } from '../utils/sumupCloud'
import { formatDateTime } from '../utils/localeFormat'

vi.mock('../utils/sumupCloud', async () => {
  const actual = await vi.importActual<typeof import('../utils/sumupCloud')>('../utils/sumupCloud')
  return {
    ...actual,
    fetchSumupReaderTelemetry: vi.fn(),
  }
})

vi.mock('../utils/localeFormat', async () => {
  const actual = await vi.importActual<typeof import('../utils/localeFormat')>(
    '../utils/localeFormat',
  )
  return {
    ...actual,
    formatDateTime: vi.fn(() => '25.09.2025, 17:20'),
  }
})

vi.mock('../i18n', () => ({
  currentLocale: () => 'de',
}))

const reader: SumupReader = {
  id: 5,
  sumup_reader_id: 'rdr_3MSAFM23CK82VSTT4BN6RWSQ65',
  label: 'Bar',
  status: 'paired',
  device_identifier: 'U1DT3NA00-CN',
  device_model: 'solo',
}

function mountTooltip() {
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })
  return mount(SumupReaderTelemetryTooltip, {
    props: { organisationId: 3, reader },
    global: {
      plugins: [i18n],
      stubs: {
        'v-tooltip': {
          template:
            '<div class="v-tooltip-stub"><slot name="activator" :props="{}" /><div class="v-tooltip-content"><slot /></div></div>',
        },
      },
    },
  })
}

describe('SumupReaderTelemetryTooltip', () => {
  beforeEach(() => {
    vi.mocked(fetchSumupReaderTelemetry).mockReset()
  })

  it('shows live telemetry after hover', async () => {
    vi.mocked(fetchSumupReaderTelemetry).mockResolvedValue({
      id: 5,
      sumup_reader_id: reader.sumup_reader_id,
      label: 'Bar',
      device_identifier: 'U1DT3NA00-CN',
      device_model: 'solo',
      telemetry_available: true,
      online_status: 'ONLINE',
      battery_level: 10.5,
      connection_type: 'Wi-Fi',
      firmware_version: '3.3.3.21',
      last_activity: '2025-09-25T15:20:00Z',
      state: 'IDLE',
    })
    const wrapper = mountTooltip()
    await wrapper.get('[data-testid="sumup-reader-label"]').trigger('mouseenter')
    await flushPromises()
    const tip = wrapper.get('[data-testid="sumup-reader-telemetry"]').text()
    expect(tip).toContain('Serial: U1DT3NA00-CN')
    expect(tip).toContain('Model: solo')
    expect(tip).toContain('Online')
    expect(tip).toContain('Battery: 10.5%')
    expect(tip).toContain('Wi-Fi')
    expect(tip).toContain('3.3.3.21')
    expect(tip).toContain('25.09.2025, 17:20')
    expect(tip).not.toContain('2025-09-25T15:20:00Z')
    expect(tip).toContain('IDLE')
    expect(fetchSumupReaderTelemetry).toHaveBeenCalledWith(3, 5)
    expect(formatDateTime).toHaveBeenCalledWith('2025-09-25T15:20:00Z', 'de')
  })

  it('shows persisted identity and unavailable copy when telemetry fails', async () => {
    vi.mocked(fetchSumupReaderTelemetry).mockResolvedValue({
      id: 5,
      sumup_reader_id: reader.sumup_reader_id,
      label: 'Bar',
      device_identifier: 'U1DT3NA00-CN',
      device_model: 'solo',
      telemetry_available: false,
      online_status: null,
      battery_level: null,
      connection_type: null,
      firmware_version: null,
      last_activity: null,
      state: null,
    })
    const wrapper = mountTooltip()
    await wrapper.get('[data-testid="sumup-reader-label"]').trigger('mouseenter')
    await flushPromises()
    const tip = wrapper.get('[data-testid="sumup-reader-telemetry"]').text()
    expect(tip).toContain('Serial: U1DT3NA00-CN')
    expect(tip).toContain('Model: solo')
    expect(tip).toContain('Live device status is unavailable')
    expect(tip).not.toContain('Battery:')
  })
})
