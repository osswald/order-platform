import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, nextTick, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { testI18n } from '../../tests/setup.js'

vi.mock('../api', () => ({
  apiJson: vi.fn(),
}))

import type { Ref } from 'vue'
import { apiJson } from '../api'
import { formatTaxCodeLabel, invalidateTaxCodesCache, useTaxCodes } from './useTaxCodes'

function mountTaxCodes(countryIdRef: Ref<number | null>) {
  let result!: ReturnType<typeof useTaxCodes>
  const Comp = defineComponent({
    setup() {
      result = useTaxCodes(countryIdRef)
      return () => null
    },
  })
  mount(Comp, { global: { plugins: [testI18n] } })
  return result
}

describe('formatTaxCodeLabel', () => {
  it('includes current rate percent in label', () => {
    const label = formatTaxCodeLabel({
      name: 'Normalsatz',
      id: 1,
      country_id: 1,
      country: { id: 1, code: 'CH', name: 'Schweiz' },
      rates: [{ id: 1, rate_percent: 8.1, valid_from: '2020-01-01', valid_to: null }],
    })
    expect(label).toBe('Normalsatz (8,1%)')
  })

  it('returns name only when no rates', () => {
    expect(formatTaxCodeLabel({
      name: 'Zero',
      id: 2,
      country_id: 1,
      country: { id: 1, code: 'CH', name: 'Schweiz' },
      rates: [],
    })).toBe('Zero')
  })

  it('ignores future rates', () => {
    const future = new Date()
    future.setFullYear(future.getFullYear() + 2)
    const label = formatTaxCodeLabel({
      name: 'Alt',
      id: 3,
      country_id: 1,
      country: { id: 1, code: 'CH', name: 'Schweiz' },
      rates: [
        { id: 1, rate_percent: 7.7, valid_from: '2018-01-01', valid_to: null },
        { id: 2, rate_percent: 99, valid_from: future.toISOString().slice(0, 10), valid_to: null },
      ],
    })
    expect(label).toBe('Alt (7,7%)')
  })
})

describe('useTaxCodes', () => {
  beforeEach(() => {
    vi.mocked(apiJson).mockReset()
    invalidateTaxCodesCache()
  })

  it('loads tax codes for country id', async () => {
    vi.mocked(apiJson).mockResolvedValue([
      { id: 10, name: 'Normalsatz', rates: [{ rate_percent: 8.1, valid_from: '2020-01-01' }] },
    ])
    const countryId = ref(1)
    const { taxCodes, options } = mountTaxCodes(countryId)

    await flushPromises()
    expect(taxCodes.value).toHaveLength(1)
    expect(apiJson).toHaveBeenCalledWith('/tax-codes/?country_id=1')
    expect(options.value[0].value).toBe(10)
  })

  it('clears tax codes when country id is null', async () => {
    const countryId = ref(null)
    const { taxCodes } = mountTaxCodes(countryId)

    await flushPromises()
    expect(taxCodes.value).toEqual([])
    expect(apiJson).not.toHaveBeenCalled()
  })

  it('uses cache per country', async () => {
    vi.mocked(apiJson).mockResolvedValue([{ id: 10, name: 'Normalsatz', rates: [] }])
    const countryId = ref(1)
    mountTaxCodes(countryId)
    await flushPromises()
    expect(apiJson).toHaveBeenCalledTimes(1)

    mountTaxCodes(ref(1))
    await nextTick()
    expect(apiJson).toHaveBeenCalledTimes(1)
  })
})
