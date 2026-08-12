import { describe, expect, it } from 'vitest'
import {
  clipRangeToMonth,
  groupFleetByType,
  occupancyOnDay,
  rentalCanDelete,
  rentalDisplayName,
  rentalIsFilled,
  rentalsOverlappingMonth,
  rentalsOverlappingYear,
} from './rentalCalendar'

describe('rentalDisplayName', () => {
  it('uses the label when set', () => {
    expect(rentalDisplayName('Openair 2026', 'FC St.Gallen')).toBe('Openair 2026')
  })

  it('falls back to organisation name when label is empty', () => {
    expect(rentalDisplayName(null, 'FC St.Gallen')).toBe('FC St.Gallen')
    expect(rentalDisplayName('  ', 'FC St.Gallen')).toBe('FC St.Gallen')
  })
})

describe('rentalIsFilled', () => {
  it('is filled when an open lending exists', () => {
    expect(rentalIsFilled([{ returned_at: null }])).toBe(true)
  })

  it('is empty when there are no open lendings', () => {
    expect(rentalIsFilled([])).toBe(false)
    expect(rentalIsFilled([{ returned_at: '2026-06-15T00:00:00Z' }])).toBe(false)
  })
})

describe('rentalCanDelete', () => {
  it('allows delete for empty or planned-only rentals', () => {
    expect(rentalCanDelete([])).toBe(true)
    expect(rentalCanDelete([{ segment: 'future' }])).toBe(true)
  })

  it('blocks delete when a current or past lending exists', () => {
    expect(rentalCanDelete([{ segment: 'current' }])).toBe(false)
    expect(rentalCanDelete([{ segment: 'past' }])).toBe(false)
    expect(rentalCanDelete([{ segment: 'future' }, { segment: 'current' }])).toBe(false)
  })
})

describe('calendar overlap', () => {
  const rental = {
    id: 1,
    displayName: 'FC St.Gallen',
    organisationId: 9,
    startDate: '2026-06-12',
    endDate: '2026-06-15',
    filled: false,
  }

  it('includes a June rental in the June month view', () => {
    const rows = rentalsOverlappingMonth([rental], 2026, 5)
    expect(rows).toHaveLength(1)
    expect(rows[0].displayName).toBe('FC St.Gallen')
  })

  it('excludes a June rental from May', () => {
    expect(rentalsOverlappingMonth([rental], 2026, 4)).toHaveLength(0)
  })

  it('includes the rental in the 2026 year view', () => {
    expect(rentalsOverlappingYear([rental], 2026)).toHaveLength(1)
    expect(rentalsOverlappingYear([rental], 2025)).toHaveLength(0)
  })

  it('clips a multi-day rental to the visible month', () => {
    const clipped = clipRangeToMonth('2026-06-12', '2026-06-15', 2026, 5)
    expect(clipped).toEqual({ start: '2026-06-12', end: '2026-06-15' })
  })
})

describe('fleet occupancy', () => {
  it('occupies assigned days and leaves empty rentals off the fleet', () => {
    const occupancy = {
      rentalId: 1,
      displayName: 'Openair 2026',
      organisationId: 9,
      startDate: '2026-06-12',
      endDate: '2026-06-15',
    }
    expect(occupancyOnDay([occupancy], '2026-06-12')?.displayName).toBe('Openair 2026')
    expect(occupancyOnDay([occupancy], '2026-06-15')?.displayName).toBe('Openair 2026')
    expect(occupancyOnDay([occupancy], '2026-06-16')).toBeNull()
    expect(occupancyOnDay([], '2026-06-12')).toBeNull()
  })

  it('does not treat an empty rental as fleet occupancy', () => {
    const emptyRental = {
      id: 9,
      displayName: 'Placeholder',
      organisationId: 1,
      startDate: '2026-06-12',
      endDate: '2026-06-15',
      filled: false,
    }
    expect(emptyRental.filled).toBe(false)
    expect(occupancyOnDay([], emptyRental.startDate)).toBeNull()
  })

  it('keeps type group order and lists unassigned appliances', () => {
    const groups = groupFleetByType([
      { type: 'printer', appliances: [{ id: 2, name: 'Drucker-01', type: 'printer', occupancies: [] }] },
      { type: 'server', appliances: [{ id: 1, name: 'Pi-01', type: 'server', occupancies: [] }] },
    ])
    expect(groups.map((g) => g.type)).toEqual(['server', 'printer'])
    expect(groups[1].appliances[0].occupancies).toEqual([])
  })
})
