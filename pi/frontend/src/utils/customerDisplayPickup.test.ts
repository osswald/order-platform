import { describe, expect, it } from 'vitest'
import type { EdgeBundleEvent } from '@/types/api'
import {
  abholbonFooterText,
  displayPickupsFromSummary,
  pickupBadgesForDisplay,
  pickupCodesForDisplay,
} from './customerDisplayPickup'

describe('pickupCodesForDisplay', () => {
  it('returns all pickup_codes', () => {
    expect(pickupCodesForDisplay({ pickup_codes: ['A1', 'A2'], pickup_code: 'A1' })).toEqual(['A1', 'A2'])
  })

  it('falls back to pickup_code', () => {
    expect(pickupCodesForDisplay({ pickup_code: 'B3' })).toEqual(['B3'])
  })

  it('returns empty when none', () => {
    expect(pickupCodesForDisplay({})).toEqual([])
  })
})

const event = {
  configuration: {
    stations: [
      { uuid: 'st-kitchen', name: 'Grill' },
      { uuid: 'st-bar', name: 'Getränke' },
    ],
  },
} as unknown as EdgeBundleEvent

describe('displayPickupsFromSummary', () => {
  it('resolves station names from the event bundle', () => {
    expect(
      displayPickupsFromSummary(
        [
          { pickup_code: 'A1', station_uuid: 'st-kitchen' },
          { pickup_code: 'A2', station_uuid: 'st-bar' },
        ],
        event,
      ),
    ).toEqual([
      { pickup_code: 'A1', station_uuid: 'st-kitchen', station_name: 'Grill' },
      { pickup_code: 'A2', station_uuid: 'st-bar', station_name: 'Getränke' },
    ])
  })

  it('keeps an explicit station_name', () => {
    expect(
      displayPickupsFromSummary([{ pickup_code: 'A1', station_uuid: 'st-kitchen', station_name: 'Grill' }], null),
    ).toEqual([{ pickup_code: 'A1', station_uuid: 'st-kitchen', station_name: 'Grill' }])
  })

  it('drops pickups without a code', () => {
    expect(displayPickupsFromSummary([{ station_uuid: 'st-kitchen' }], event)).toEqual([])
  })
})

describe('pickupBadgesForDisplay', () => {
  it('uses pickups with station names', () => {
    expect(
      pickupBadgesForDisplay(
        {
          pickup_codes: ['A1', 'A2'],
          pickups: [
            { pickup_code: 'A1', station_uuid: 'st-kitchen' },
            { pickup_code: 'A2', station_uuid: 'st-bar' },
          ],
        },
        event,
      ),
    ).toEqual([
      { code: 'A1', stationName: 'Grill' },
      { code: 'A2', stationName: 'Getränke' },
    ])
  })

  it('falls back to codes when pickups are missing', () => {
    expect(pickupBadgesForDisplay({ pickup_codes: ['A1'], pickup_code: 'A1' })).toEqual([
      { code: 'A1', stationName: '' },
    ])
  })
})

describe('abholbonFooterText', () => {
  it('singular for one', () => {
    expect(abholbonFooterText(1)).toBe('Bitte Abholbon mitnehmen')
  })

  it('plural for two or more', () => {
    expect(abholbonFooterText(2)).toBe('Bitte Abholbons mitnehmen')
    expect(abholbonFooterText(3)).toBe('Bitte Abholbons mitnehmen')
  })
})
