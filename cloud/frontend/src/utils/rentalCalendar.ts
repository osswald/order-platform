import { APPLIANCE_TYPES } from './applianceType'

export interface RentalBar {
  id: number
  displayName: string
  organisationId: number
  startDate: string
  endDate: string
  filled: boolean
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
