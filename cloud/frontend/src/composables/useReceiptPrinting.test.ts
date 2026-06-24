import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, nextTick, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import {
  defaultReceiptConfig,
  defaultReceiptProfile,
  useReceiptPrinting,
} from './useReceiptPrinting'

vi.mock('../api', () => ({
  apiJson: vi.fn(),
  apiFetch: vi.fn(),
}))

import type { Ref } from 'vue'
import { apiJson } from '../api'

function mountReceiptPrinting(
  apiBasePathRef: Ref<string>,
  options: Record<string, unknown> = {},
) {
  let result!: ReturnType<typeof useReceiptPrinting>
  const Comp = defineComponent({
    setup() {
      result = useReceiptPrinting(apiBasePathRef, options)
      return () => null
    },
  })
  mount(Comp)
  return result
}

describe('defaultReceiptProfile', () => {
  it('uses xlarge table size for customer receipts', () => {
    expect(defaultReceiptProfile('customer').size_table_or_pickup).toBe('xlarge')
  })

  it('uses large table size for station receipts', () => {
    expect(defaultReceiptProfile('station').size_table_or_pickup).toBe('large')
  })
})

describe('defaultReceiptConfig', () => {
  it('includes label_event_title for events', () => {
    expect(defaultReceiptConfig(true)).toHaveProperty('label_event_title', '')
  })
})

describe('useReceiptPrinting', () => {
  beforeEach(() => {
    vi.mocked(apiJson).mockReset()
  })

  it('loads receipt config from API', async () => {
    vi.mocked(apiJson).mockResolvedValue({
      config: { station_receipt: { show_price: true } },
      has_receipt_logo: false,
    })
    const basePath = ref('/events/1')
    const api = mountReceiptPrinting(basePath)

    await api.load()
    await flushPromises()

    expect(apiJson).toHaveBeenCalledWith('/events/1/receipt-printing')
    expect(api.config.value.station_receipt.show_price).toBe(true)
    expect(api.loading.value).toBe(false)
  })

  it('autosaves when enabled and config changes', async () => {
    vi.useFakeTimers()
    vi.mocked(apiJson)
      .mockResolvedValueOnce({
        config: {},
        has_receipt_logo: false,
      })
      .mockResolvedValue({
        config: { station_receipt: { show_price: true } },
        has_receipt_logo: false,
      })

    const basePath = ref('/events/2')
    const api = mountReceiptPrinting(basePath, { isEvent: true, autosave: true })

    await api.load()
    await flushPromises()
    api.config.value = {
      ...api.config.value,
      station_receipt: { ...api.config.value.station_receipt, show_price: true },
    }
    await nextTick()

    vi.advanceTimersByTime(800)
    await flushPromises()

    expect(apiJson).toHaveBeenCalledWith(
      '/events/2/receipt-printing',
      expect.objectContaining({ method: 'PUT' }),
    )
    vi.useRealTimers()
  })
})
