import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, nextTick } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { testI18n } from '../../tests/setup.js'

vi.mock('../api', () => ({
  apiJson: vi.fn(),
}))

import { apiJson } from '../api'
import {
  invalidatePaymentTypesCache,
  paymentTypeLabel,
  usePaymentTypes,
} from './usePaymentTypes'

function mountPaymentTypes(options: Record<string, unknown> = {}) {
  let result!: ReturnType<typeof usePaymentTypes>
  const Comp = defineComponent({
    setup() {
      result = usePaymentTypes(options)
      return () => null
    },
  })
  mount(Comp, { global: { plugins: [testI18n] } })
  return result
}

describe('paymentTypeLabel', () => {
  it('returns translation when available', () => {
    const t = (key: string) => (key === 'paymentTypes.cash' ? 'Bar' : key)
    expect(paymentTypeLabel('cash', t)).toBe('Bar')
  })

  it('falls back to slug when no translation', () => {
    const t = (key: string) => key
    expect(paymentTypeLabel('custom', t)).toBe('custom')
  })
})

describe('usePaymentTypes', () => {
  beforeEach(() => {
    vi.mocked(apiJson).mockReset()
    invalidatePaymentTypesCache()
  })

  it('loads active payment types by default', async () => {
    vi.mocked(apiJson).mockResolvedValue([
      { id: 1, slug: 'cash', sort_order: 0, is_active: true },
    ])
    const { paymentTypes, options } = mountPaymentTypes()

    await flushPromises()
    expect(paymentTypes.value).toHaveLength(1)
    expect(apiJson).toHaveBeenCalledWith('/payment-types/?active_only=true')
    expect(options.value[0].value).toBe('cash')
  })

  it('uses module cache on second composable instance', async () => {
    vi.mocked(apiJson).mockResolvedValue([{ id: 1, slug: 'cash', sort_order: 0, is_active: true }])
    mountPaymentTypes()
    await flushPromises()
    expect(apiJson).toHaveBeenCalledTimes(1)

    mountPaymentTypes()
    await nextTick()
    expect(apiJson).toHaveBeenCalledTimes(1)
  })

  it('loads all payment types when activeOnly is false', async () => {
    vi.mocked(apiJson).mockResolvedValue([{ id: 2, slug: 'card', sort_order: 1, is_active: false }])
    const { paymentTypes } = mountPaymentTypes({ activeOnly: false })

    await flushPromises()
    expect(paymentTypes.value).toHaveLength(1)
    expect(apiJson).toHaveBeenCalledWith('/payment-types/')
  })

  it('sets loadError on failure', async () => {
    vi.mocked(apiJson).mockRejectedValue(new Error('network down'))
    const { loadError, paymentTypes } = mountPaymentTypes()

    await flushPromises()
    expect(loadError.value).toBe('network down')
    expect(paymentTypes.value).toEqual([])
  })
})
