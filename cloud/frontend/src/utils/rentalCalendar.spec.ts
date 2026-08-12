import { describe, expect, it } from 'vitest'
import {
  assignColumnLanes,
  assignIntervalLanes,
  clipRangeToMonth,
  groupFleetByType,
  monthBarSegments,
  monthWeeks,
  occupancyOnDay,
  rentalCanDelete,
  rentalDisplayName,
  rentalIsFilled,
  openRentalApplianceNames,
  rentalsOverlappingMonth,
  rentalsOverlappingYear,
  yearBarsWithLanes,
} from './rentalCalendar'

function bar(partial: Partial<Parameters<typeof rentalsOverlappingMonth>[0][number]> & { id: number; displayName: string }) {
  return {
    organisationId: 9,
    organisationName: 'FC St.Gallen',
    startDate: '2026-06-12',
    endDate: '2026-06-15',
    filled: false,
    applianceNames: [] as string[],
    ...partial,
  }
}

describe('rentalDisplayName', () => {
  it('uses the label when set', () => {
    expect(rentalDisplayName('Openair 2026', 'FC St.Gallen')).toBe('Openair 2026')
  })

  it('falls back to organisation name when label is empty', () => {
    expect(rentalDisplayName(null, 'FC St.Gallen')).toBe('FC St.Gallen')
    expect(rentalDisplayName('  ', 'FC St.Gallen')).toBe('FC St.Gallen')
  })
})

describe('openRentalApplianceNames', () => {
  it('lists open appliances and skips returned ones', () => {
    expect(
      openRentalApplianceNames([
        { appliance_id: 1, appliance_name: 'Pi-01', returned_at: null },
        { appliance_id: 2, appliance_name: 'Pi-02', returned_at: '2026-06-10T00:00:00Z' },
        { appliance_id: 3, appliance_name: null, returned_at: null },
      ]),
    ).toEqual(['Pi-01', '#3'])
  })

  it('dedupes by appliance id', () => {
    expect(
      openRentalApplianceNames([
        { appliance_id: 1, appliance_name: 'Pi-01', returned_at: null },
        { appliance_id: 1, appliance_name: 'Pi-01', returned_at: null },
      ]),
    ).toEqual(['Pi-01'])
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
  const rental = bar({
    id: 1,
    displayName: 'FC St.Gallen',
    organisationId: 9,
    startDate: '2026-06-12',
    endDate: '2026-06-15',
    filled: false,
  })

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

describe('lane packing', () => {
  it('puts overlapping intervals on separate lanes', () => {
    const lanes = assignIntervalLanes([
      { id: 1, start: '2026-09-17', end: '2026-09-21' },
      { id: 2, start: '2026-09-17', end: '2026-09-21' },
      { id: 3, start: '2026-09-22', end: '2026-09-24' },
    ])
    expect(lanes.get(1)).toBe(0)
    expect(lanes.get(2)).toBe(1)
    expect(lanes.get(3)).toBe(0)
  })

  it('packs column ranges within a week', () => {
    const lanes = assignColumnLanes([
      { id: 1, startCol: 0, endCol: 2 },
      { id: 2, startCol: 1, endCol: 3 },
      { id: 3, startCol: 3, endCol: 4 },
    ])
    expect(lanes.get(1)).toBe(0)
    expect(lanes.get(2)).toBe(1)
    expect(lanes.get(3)).toBe(0)
  })

  it('stacks overlapping year-month bars on separate lanes', () => {
    const bars = yearBarsWithLanes(
      [
        bar({
          id: 21,
          displayName: 'SBB',
          organisationId: 3,
          organisationName: 'SBB',
          startDate: '2026-09-17',
          endDate: '2026-09-21',
          filled: false,
        }),
        bar({
          id: 22,
          displayName: 'SBB',
          organisationId: 3,
          organisationName: 'SBB',
          startDate: '2026-09-17',
          endDate: '2026-09-21',
          filled: false,
        }),
      ],
      2026,
      8,
    )
    expect(bars).toHaveLength(2)
    expect(new Set(bars.map((b) => b.lane)).size).toBe(2)
  })
})

describe('month spanning bars', () => {
  it('emits one segment per week for a multi-day rental', () => {
    // Fri 12 Jun – Mon 15 Jun 2026 spans two week rows (not one chip per day).
    const segments = monthBarSegments(
      [
        bar({
          id: 1,
          displayName: 'FC St.Gallen',
          organisationId: 9,
          startDate: '2026-06-12',
          endDate: '2026-06-15',
          filled: false,
        }),
      ],
      2026,
      5,
    )
    expect(segments).toHaveLength(2)
    expect(segments.every((seg) => seg.rentalId === 1)).toBe(true)
    expect(segments[0].endCol).toBeGreaterThanOrEqual(segments[0].startCol)
  })

  it('keeps a within-week rental as a single bar', () => {
    const segments = monthBarSegments(
      [
        bar({
          id: 1,
          displayName: 'Short',
          organisationId: 9,
          startDate: '2026-06-08',
          endDate: '2026-06-11',
          filled: true,
        }),
      ],
      2026,
      5,
    )
    expect(segments).toHaveLength(1)
    expect(segments[0].startCol).toBe(0)
    expect(segments[0].endCol).toBe(3)
  })

  it('builds week rows of seven cells', () => {
    const weeks = monthWeeks(2026, 5)
    expect(weeks.length).toBeGreaterThanOrEqual(4)
    expect(weeks.every((week) => week.length === 7)).toBe(true)
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
