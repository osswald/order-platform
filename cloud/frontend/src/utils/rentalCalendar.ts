import { APPLIANCE_TYPES } from './applianceType'

export interface RentalBar {
  id: number
  displayName: string
  organisationId: number
  organisationName: string
  startDate: string
  endDate: string
  filled: boolean
  applianceNames: string[]
}

/** Open (not returned) appliance labels for calendar tooltips. */
export function openRentalApplianceNames(
  lendings:
    | Array<{
        appliance_id: number
        appliance_name?: string | null
        returned_at?: string | null
      }>
    | null
    | undefined,
): string[] {
  const names: string[] = []
  const seen = new Set<number>()
  for (const row of lendings ?? []) {
    if (row.returned_at) continue
    if (seen.has(row.appliance_id)) continue
    seen.add(row.appliance_id)
    const trimmed = (row.appliance_name ?? '').trim()
    names.push(trimmed || `#${row.appliance_id}`)
  }
  return names
}

export interface FleetOccupancy {
  rentalId: number
  displayName: string
  organisationId: number
  startDate: string
  endDate: string
}

export interface FleetAppliance {
  id: number
  name: string | null
  type: string
  occupancies: FleetOccupancy[]
}

export interface FleetTypeGroup {
  type: string
  appliances: FleetAppliance[]
}

export function rentalDisplayName(label: string | null | undefined, organisationName: string): string {
  const trimmed = (label ?? '').trim()
  return trimmed || organisationName
}

export function rentalIsFilled(lendings: Array<{ returned_at?: string | null }> | null | undefined): boolean {
  return (lendings ?? []).some((row) => !row.returned_at)
}

/** Mirrors server delete rules: empty or planned-only (future) lendings; not current/history. */
export function rentalCanDelete(lendings: Array<{ segment: string }> | null | undefined): boolean {
  return (lendings ?? []).every((row) => row.segment === 'future')
}

export function organisationBarColor(organisationId: number): string {
  const hue = (organisationId * 47) % 360
  return `hsl(${hue} 42% 42%)`
}

export function isoDate(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function parseIsoDate(value: string): Date {
  const [y, m, d] = value.split('-').map(Number)
  return new Date(y, (m ?? 1) - 1, d ?? 1)
}

export function datesOverlap(aStart: string, aEnd: string, bStart: string, bEnd: string): boolean {
  return aStart <= bEnd && bStart <= aEnd
}

export interface MonthCell {
  iso: string
  date: Date
  inMonth: boolean
}

export function monthGrid(year: number, month: number): MonthCell[] {
  const first = new Date(year, month, 1)
  const startWeekday = (first.getDay() + 6) % 7
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const cells: MonthCell[] = []
  for (let i = 0; i < startWeekday; i += 1) {
    const d = new Date(year, month, 1 - (startWeekday - i))
    cells.push({ iso: isoDate(d), date: d, inMonth: false })
  }
  for (let day = 1; day <= daysInMonth; day += 1) {
    const d = new Date(year, month, day)
    cells.push({ iso: isoDate(d), date: d, inMonth: true })
  }
  while (cells.length % 7 !== 0) {
    const last = cells[cells.length - 1].date
    const d = new Date(last.getFullYear(), last.getMonth(), last.getDate() + 1)
    cells.push({ iso: isoDate(d), date: d, inMonth: false })
  }
  return cells
}

export function rentalsOverlappingMonth(rentals: RentalBar[], year: number, month: number): RentalBar[] {
  const start = isoDate(new Date(year, month, 1))
  const end = isoDate(new Date(year, month + 1, 0))
  return rentals.filter((r) => datesOverlap(r.startDate, r.endDate, start, end))
}

export function rentalsOverlappingYear(rentals: RentalBar[], year: number): RentalBar[] {
  const start = `${year}-01-01`
  const end = `${year}-12-31`
  return rentals.filter((r) => datesOverlap(r.startDate, r.endDate, start, end))
}

export function clipRangeToMonth(
  startDate: string,
  endDate: string,
  year: number,
  month: number,
): { start: string; end: string } | null {
  const monthStart = isoDate(new Date(year, month, 1))
  const monthEnd = isoDate(new Date(year, month + 1, 0))
  if (!datesOverlap(startDate, endDate, monthStart, monthEnd)) return null
  return {
    start: startDate < monthStart ? monthStart : startDate,
    end: endDate > monthEnd ? monthEnd : endDate,
  }
}

export function occupancyOnDay(occupancies: FleetOccupancy[], iso: string): FleetOccupancy | null {
  return occupancies.find((row) => row.startDate <= iso && iso <= row.endDate) ?? null
}

/** Pack inclusive date intervals into non-overlapping lanes (greedy by start). */
export function assignIntervalLanes(
  items: Array<{ id: number; start: string; end: string }>,
): Map<number, number> {
  const sorted = [...items].sort(
    (a, b) => a.start.localeCompare(b.start) || a.end.localeCompare(b.end) || a.id - b.id,
  )
  const laneEnds: string[] = []
  const lanes = new Map<number, number>()
  for (const item of sorted) {
    let lane = laneEnds.findIndex((end) => end < item.start)
    if (lane === -1) {
      lane = laneEnds.length
      laneEnds.push(item.end)
    } else {
      laneEnds[lane] = item.end
    }
    lanes.set(item.id, lane)
  }
  return lanes
}

/** Pack inclusive column ranges (0–6) into lanes within one week. */
export function assignColumnLanes(
  items: Array<{ id: number; startCol: number; endCol: number }>,
): Map<number, number> {
  const sorted = [...items].sort(
    (a, b) => a.startCol - b.startCol || a.endCol - b.endCol || a.id - b.id,
  )
  const laneEnds: number[] = []
  const lanes = new Map<number, number>()
  for (const item of sorted) {
    let lane = laneEnds.findIndex((end) => end < item.startCol)
    if (lane === -1) {
      lane = laneEnds.length
      laneEnds.push(item.endCol)
    } else {
      laneEnds[lane] = item.endCol
    }
    lanes.set(item.id, lane)
  }
  return lanes
}

export function yearBarsWithLanes(
  rentals: RentalBar[],
  year: number,
  month: number,
): Array<RentalBar & { lane: number; clipStart: string; clipEnd: string }> {
  const overlapping = rentalsOverlappingMonth(rentals, year, month)
  const clipped = overlapping
    .map((bar) => {
      const clip = clipRangeToMonth(bar.startDate, bar.endDate, year, month)
      if (!clip) return null
      return { ...bar, clipStart: clip.start, clipEnd: clip.end }
    })
    .filter((row): row is RentalBar & { clipStart: string; clipEnd: string } => row != null)
  const lanes = assignIntervalLanes(
    clipped.map((bar) => ({ id: bar.id, start: bar.clipStart, end: bar.clipEnd })),
  )
  return clipped.map((bar) => ({ ...bar, lane: lanes.get(bar.id) ?? 0 }))
}

export interface MonthBarSegment {
  rentalId: number
  displayName: string
  organisationId: number
  filled: boolean
  weekIndex: number
  startCol: number
  endCol: number
  lane: number
}

/** One continuous bar segment per rental per week row in the month grid. */
export function monthBarSegments(rentals: RentalBar[], year: number, month: number): MonthBarSegment[] {
  const cells = monthGrid(year, month)
  const weekCount = Math.floor(cells.length / 7)
  const raw: Array<Omit<MonthBarSegment, 'lane'>> = []

  for (const rental of rentals) {
    const clipped = clipRangeToMonth(rental.startDate, rental.endDate, year, month)
    if (!clipped) continue
    for (let weekIndex = 0; weekIndex < weekCount; weekIndex += 1) {
      let startCol = -1
      let endCol = -1
      for (let col = 0; col < 7; col += 1) {
        const cell = cells[weekIndex * 7 + col]
        if (cell.iso >= clipped.start && cell.iso <= clipped.end) {
          if (startCol === -1) startCol = col
          endCol = col
        }
      }
      if (startCol !== -1) {
        raw.push({
          rentalId: rental.id,
          displayName: rental.displayName,
          organisationId: rental.organisationId,
          filled: rental.filled,
          weekIndex,
          startCol,
          endCol,
        })
      }
    }
  }

  const result: MonthBarSegment[] = []
  for (let weekIndex = 0; weekIndex < weekCount; weekIndex += 1) {
    const weekRaw = raw.filter((seg) => seg.weekIndex === weekIndex)
    const lanes = assignColumnLanes(
      weekRaw.map((seg) => ({ id: seg.rentalId, startCol: seg.startCol, endCol: seg.endCol })),
    )
    for (const seg of weekRaw) {
      result.push({ ...seg, lane: lanes.get(seg.rentalId) ?? 0 })
    }
  }
  return result
}

export function monthWeeks(year: number, month: number): MonthCell[][] {
  const cells = monthGrid(year, month)
  const weeks: MonthCell[][] = []
  for (let i = 0; i < cells.length; i += 7) {
    weeks.push(cells.slice(i, i + 7))
  }
  return weeks
}

export function groupFleetByType(groups: FleetTypeGroup[]): FleetTypeGroup[] {
  const order = [...APPLIANCE_TYPES]
  const byType = new Map(groups.map((g) => [g.type, g]))
  const ordered: FleetTypeGroup[] = []
  for (const type of order) {
    const group = byType.get(type)
    if (group) ordered.push(group)
  }
  for (const group of groups) {
    if (!order.includes(group.type as (typeof APPLIANCE_TYPES)[number])) ordered.push(group)
  }
  return ordered
}
