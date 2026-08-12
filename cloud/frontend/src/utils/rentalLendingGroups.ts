/** Group appliance lendings under rentals (newest rental first). */

export interface LendingWithRental {
  id: number
  rental_id?: number | null
  rental_display_name?: string | null
  start_date: string
  organisation_name?: string
}

export interface LendingRentalGroup<T extends LendingWithRental = LendingWithRental> {
  rentalId: number
  displayName: string
  startDate: string
  lendings: T[]
}

export function groupLendingsByRentalNewestFirst<T extends LendingWithRental>(
  lendings: T[],
): LendingRentalGroup<T>[] {
  const byRental = new Map<number, LendingRentalGroup<T>>()
  for (const row of lendings) {
    const rentalId = row.rental_id ?? 0
    const existing = byRental.get(rentalId)
    if (existing) {
      existing.lendings.push(row)
      if (row.start_date > existing.startDate) existing.startDate = row.start_date
      continue
    }
    byRental.set(rentalId, {
      rentalId,
      displayName: (row.rental_display_name || row.organisation_name || `#${rentalId}`).trim() || `#${rentalId}`,
      startDate: row.start_date,
      lendings: [row],
    })
  }
  return [...byRental.values()].sort((a, b) => {
    if (a.startDate !== b.startDate) return a.startDate < b.startDate ? 1 : -1
    return b.rentalId - a.rentalId
  })
}

export function sortRentalsNewestFirst<T extends { start_date: string; id: number }>(rows: T[]): T[] {
  return [...rows].sort((a, b) => {
    if (a.start_date !== b.start_date) return a.start_date < b.start_date ? 1 : -1
    return b.id - a.id
  })
}

/** Inclusive ranges share more than an endpoint day (matches backend handover rule). */
export function rangesStrictlyOverlap(
  startA: string,
  endA: string,
  startB: string,
  endB: string,
): boolean {
  return startA < endB && startB < endA
}
