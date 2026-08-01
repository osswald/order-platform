import { describe, expect, it } from 'vitest'
import type { EdgeBundleEvent, EdgeBundleResponse } from '@/types/api'
import {
  autoSelectSumupReader,
  eventNeedsSumupReaderPicker,
  getBundleSumupReaders,
  resolveRegisterSumupReaderId,
} from './sumupReaders'

const readers = [
  { sumup_reader_id: 'r1', label: 'Bar' },
  { sumup_reader_id: 'r2', label: 'Terrasse' },
]

describe('sumupReaders', () => {
  it('returns empty list when bundle has no sumup_readers', () => {
    expect(getBundleSumupReaders({ organisation_id: 1, events: [] } as EdgeBundleResponse)).toEqual([])
  })

  it('reads labelled readers from bundle', () => {
    expect(
      getBundleSumupReaders({
        organisation_id: 1,
        events: [],
        sumup_readers: readers,
      } as EdgeBundleResponse),
    ).toEqual(readers)
  })

  it('requires picker when sumup_connected and multiple readers', () => {
    const event = { payment_types: ['cash', 'sumup_connected'] } as EdgeBundleEvent
    expect(eventNeedsSumupReaderPicker(event, readers)).toBe(true)
  })

  it('does not require picker without sumup_connected', () => {
    const event = { payment_types: ['cash'] } as EdgeBundleEvent
    expect(eventNeedsSumupReaderPicker(event, readers)).toBe(false)
  })

  it('auto-selects when exactly one reader', () => {
    expect(autoSelectSumupReader([{ sumup_reader_id: 'r1', label: 'Bar' }])).toEqual({
      sumup_reader_id: 'r1',
      label: 'Bar',
    })
    expect(autoSelectSumupReader(readers)).toBeNull()
  })

  it('reads register default sumup_reader_id from event config', () => {
    const event = {
      configuration: {
        cash_registers: [{ uuid: 'reg-1', name: 'Front', sumup_reader_id: 'r2' }],
      },
    } as EdgeBundleEvent
    expect(resolveRegisterSumupReaderId(event, 'reg-1')).toBe('r2')
    expect(resolveRegisterSumupReaderId(event, 'missing')).toBeNull()
  })
})
