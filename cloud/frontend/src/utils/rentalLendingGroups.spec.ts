import { describe, expect, it } from 'vitest'
import {
  groupLendingsByRentalNewestFirst,
  rangesStrictlyOverlap,
  sortRentalsNewestFirst,
} from './rentalLendingGroups'

describe('rentalLendingGroups', () => {
  it('groups lendings by rental newest first', () => {
    const groups = groupLendingsByRentalNewestFirst([
      {
        id: 1,
        rental_id: 10,
        rental_display_name: 'Older',
        start_date: '2026-01-01',
      },
      {
        id: 2,
        rental_id: 20,
        rental_display_name: 'Newer',
        start_date: '2026-06-01',
      },
      {
        id: 3,
        rental_id: 20,
        rental_display_name: 'Newer',
        start_date: '2026-06-01',
      },
    ])
    expect(groups).toHaveLength(2)
    expect(groups[0].rentalId).toBe(20)
    expect(groups[0].lendings).toHaveLength(2)
    expect(groups[1].rentalId).toBe(10)
  })

  it('sorts rentals newest first', () => {
    const sorted = sortRentalsNewestFirst([
      { id: 1, start_date: '2026-01-01' },
      { id: 3, start_date: '2026-06-01' },
      { id: 2, start_date: '2026-06-01' },
    ])
    expect(sorted.map((r) => r.id)).toEqual([3, 2, 1])
  })

  it('allows handover-day touch but rejects interior overlap', () => {
    expect(rangesStrictlyOverlap('2026-06-01', '2026-06-15', '2026-06-15', '2026-06-20')).toBe(false)
    expect(rangesStrictlyOverlap('2026-06-01', '2026-06-15', '2026-06-14', '2026-06-20')).toBe(true)
  })
})
