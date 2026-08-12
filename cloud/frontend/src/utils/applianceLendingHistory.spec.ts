import { describe, expect, it } from 'vitest'
import { groupLendingsByRentalNewestFirst } from '../utils/rentalLendingGroups'

describe('appliance lending history grouping', () => {
  it('orders rental groups newest first for history panels', () => {
    const groups = groupLendingsByRentalNewestFirst([
      {
        id: 1,
        rental_id: 1,
        rental_display_name: 'Spring',
        start_date: '2026-03-01',
        organisation_name: 'Org',
      },
      {
        id: 2,
        rental_id: 2,
        rental_display_name: 'Summer',
        start_date: '2026-07-01',
        organisation_name: 'Org',
      },
    ])
    expect(groups.map((g) => g.displayName)).toEqual(['Summer', 'Spring'])
  })
})
