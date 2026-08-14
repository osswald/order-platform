import { describe, expect, it } from 'vitest'
import { abholbonFooterText, pickupCodesForDisplay } from './customerDisplayPickup'

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

describe('abholbonFooterText', () => {
  it('singular for one', () => {
    expect(abholbonFooterText(1)).toBe('Bitte Abholbon mitnehmen')
  })

  it('plural for two or more', () => {
    expect(abholbonFooterText(2)).toBe('Bitte Abholbons mitnehmen')
    expect(abholbonFooterText(3)).toBe('Bitte Abholbons mitnehmen')
  })
})
